import atexit
import os
import pathlib
import subprocess
import traceback
from contextlib import suppress
from queue import Queue
from threading import Thread
from typing import IO, Self

import psutil
from PySide6.QtCore import QByteArray, QIODeviceBase, QObject, QRunnable, QTemporaryFile, QThreadPool, Signal

from songs_to_youtube.field import SETTINGS_VALUES
from songs_to_youtube.log import applogger
from songs_to_youtube.progress_worker import BaseProgressWorker
from songs_to_youtube.settings import get_setting
from songs_to_youtube.song_tree_widget_item import AlbumTreeWidgetItem, SongTreeWidgetItem

PROCESSES: list[subprocess.Popen[bytes]] = []

type SongWorker = RenderSongWorker | CombineSongWorker


# make sure to stop all the ffmpeg processes from running
# if we close the application
def clean_up() -> None:
    for p in PROCESSES:
        with suppress(Exception):
            process = psutil.Process(p.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()


atexit.register(clean_up)


class ProcessHandler(QObject):
    stdout = Signal(str)
    stderr = Signal(str)

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def read_pipe(pipe: IO[bytes], queue: Queue[tuple[IO[bytes] | None, str | None]]) -> None:
        try:
            with pipe:
                for line in iter(pipe.readline, b""):
                    queue.put((pipe, line.decode("utf-8")))
        finally:
            queue.put((None, None))

    def run(self, command: str) -> int:
        if os.name == "nt":
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True,
            )
        else:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )

        PROCESSES.append(process)
        queue: Queue[tuple[IO[bytes] | None, str | None]] = Queue()
        Thread(target=self.read_pipe, args=[process.stdout, queue]).start()
        Thread(target=self.read_pipe, args=[process.stderr, queue]).start()
        while True:
            pipe, line = queue.get()
            if pipe is None:
                break
            if pipe == process.stdout:
                self.stdout.emit(line)
            else:
                self.stderr.emit(line)
        error = process.wait() != 0
        PROCESSES.remove(process)
        return error


class RenderWorkerSignals(QObject):
    finished = Signal(bool)
    error = Signal(str)
    progress = Signal(str)


class RenderSongWorker(QRunnable):
    def __init__(self, song: SongTreeWidgetItem, *, auto_delete: bool) -> None:
        super().__init__()
        self.auto_delete = auto_delete
        self.song = song
        self.name = self.song.get("fileOutput")
        self.signals = RenderWorkerSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            command_str = (self.song.get("commandString")).format(**self.song.to_dict())
            handler = ProcessHandler()
            handler.stderr.connect(self.signals.error.emit)
            handler.stdout.connect(self.signals.progress.emit)
            errors = handler.run(command_str)
            self.signals.finished.emit(not errors)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
            finished = False
            self.signals.finished.emit(finished)

    def get_duration_ms(self) -> float:
        return self.song.get_duration_ms()

    def __str__(self) -> str:
        return self.name


class CombineSongWorker(QRunnable):
    def __init__(self, album: AlbumTreeWidgetItem) -> None:
        super().__init__()
        self.auto_delete = True
        self.album = album
        self.name = self.album.get("fileOutput")
        self.signals = RenderWorkerSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            song_list = QTemporaryFile()
            song_list.open(
                QIODeviceBase.OpenModeFlag.WriteOnly
                | QIODeviceBase.OpenModeFlag.Append
                | QIODeviceBase.OpenModeFlag.Text
            )
            for song in self.album.getChildren():
                file_output = song.get("fileOutput").replace("'", "'\\''")
                file_str = f"file 'file:{file_output}'\n"
                song_list.write(QByteArray(file_str.encode()))
            song_list.close()
            command_str = self.album.get("concatCommandString").format(
                input_file_list=song_list.fileName(),
                fileOutputPath=self.album.get("fileOutput"),
            )
            handler = ProcessHandler()
            handler.stderr.connect(self.signals.error.emit)
            handler.stdout.connect(self.signals.progress.emit)
            errors = handler.run(command_str)
            self.signals.finished.emit(not errors)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
            finished = False
            self.signals.finished.emit(finished)
        finally:
            for song in self.album.getChildren():
                with suppress(OSError):
                    pathlib.Path(song.get("fileOutput")).unlink()

    def get_duration_ms(self) -> float:
        return self.album.get_duration_ms()

    def __str__(self) -> str:
        return self.name


class AlbumRenderHelper:
    def __init__(self, album: AlbumTreeWidgetItem) -> None:
        self.album = album
        self.workers: set[str] = set()
        self.renderer = None
        self.combine_worker = ""
        self.error = False

    def worker_done(self, worker: SongWorker, *, success: bool) -> None:
        if worker in self.workers:
            self.workers.discard(worker)
            if self.renderer and not success:
                self.error = True
                self.renderer.cancel_worker(self.combine_worker)
        if self.renderer and len(self.workers) == 0 and not self.error:
            # done rendering songs,
            # begin concatenation
            self.renderer.start_worker(self.combine_worker)

    def render(self, renderer: "Renderer") -> Self:
        renderer.worker_done.connect(self.worker_done)
        for song in self.album.getChildren():
            song.before_render()
            worker = renderer.add_render_song_job(song, auto_delete=False)
            self.workers.add(worker)
        self.combine_worker = renderer.combine_songs_into_album(self.album)
        self.renderer = renderer
        return self


class Renderer(BaseProgressWorker):
    # emit true on success, false on failure
    finished = Signal(dict[str, bool])

    # worker name, worker progress (percentage)
    worker_progress = Signal(str, int)

    # worker name, worker error
    worker_error = Signal(str, str)

    # worker name
    worker_done = Signal(str, bool)

    def __init__(self) -> None:
        super().__init__()

        QThreadPool.globalInstance().setMaxThreadCount(int(get_setting("maxProcesses")))

        # array of album helpers so they
        # don't get garbage collected
        self.helpers: list[AlbumRenderHelper] = []

        # worker name -> QRunnable
        self.workers: dict[str, SongWorker] = {}

        # worker name -> QRunnable
        # workers which are not in the thread pool yet
        self.queued_workers: dict[str, SongWorker] = {}

        # finished workers that still need to be held onto
        # so that resources don't go out of scope
        self.finished_workers: list[SongWorker] = []

        # output file -> success
        self.results: dict[str, bool] = {}

        self.cancelled: bool = False

    def _worker_progress(self, worker: SongWorker, progress: str) -> None:
        key, value = progress.strip().split("=")
        if key == "out_time_us":
            if value.lower() == "n/a":
                value = "0"
            current_time_ms = int(value) // 1000
            total_time_ms = worker.get_duration_ms()
            new_progress = max(0, min(int((current_time_ms / total_time_ms) * 100), 100))
            self.worker_progress.emit(str(worker), new_progress)

    def worker_finished(self, worker: SongWorker, *, success: bool) -> None:
        self.results[str(worker)] = success
        self.workers.pop(str(worker), None)

        if self.cancelled:
            return

        if not worker.auto_delete:
            self.finished_workers.append(worker)

        self.worker_done.emit(str(worker), success)
        applogger.debug("%s finished, success: %s", str(worker), success)

        if len(self.workers) == 0:
            if len(self.queued_workers) == 0:
                # finished all jobs, send results
                self.finished.emit(self.results)
            else:
                # still have combine jobs, move them to thread pool
                for queued_worker in self.queued_workers.values():
                    self.add_worker(queued_worker)
                self.queued_workers = {}

    def start_worker(self, worker_name: str) -> None:
        # manually start a worker that wasn't created
        # with auto_start=True
        if worker_name in self.queued_workers:
            worker = self.queued_workers.pop(worker_name)
            self.workers[worker_name] = worker
            QThreadPool.globalInstance().start(worker)

    def cancel_worker(self, worker_name: str) -> None:
        # cancel a worker which is not in the thread pool yet
        self.queued_workers.pop(worker_name, None)

    def add_worker(self, worker: SongWorker, *, auto_start: bool = True) -> SongWorker:
        def worker_finished_fn(*, success: bool) -> None:
            self.worker_finished(worker, success=success)

        def worker_error_fn(error: str) -> None:
            self.worker_error.emit(str(worker), error)

        def worker_progress_fn(progress: str) -> None:
            self._worker_progress(worker, progress)

        worker.signals.finished.connect(worker_finished_fn)
        worker.signals.error.connect(worker_error_fn)
        worker.signals.progress.connect(worker_progress_fn)

        if auto_start:
            self.workers[str(worker)] = worker
            QThreadPool.globalInstance().start(worker)
        else:
            self.queued_workers[str(worker)] = worker

        return worker

    def add_render_album_job(self, album: AlbumTreeWidgetItem) -> None:
        album.before_render()
        if album.childCount() == 0:
            return
        if album.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.SINGLE:
            self.helpers.append(AlbumRenderHelper(album).render(self))
        elif album.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.MULTIPLE:
            for song in album.getChildren():
                self.add_render_song_job(song)

    def add_render_song_job(self, song: SongTreeWidgetItem, *, auto_delete: bool = True) -> str:
        song.before_render()
        worker = RenderSongWorker(song, auto_delete=auto_delete)
        self.add_worker(worker)
        return str(worker)

    def combine_songs_into_album(self, album: AlbumTreeWidgetItem) -> str:
        worker = CombineSongWorker(album)
        self.add_worker(worker, auto_start=False)
        return str(worker)

    def render(self) -> None:
        if len(self.workers) == 0 and len(self.finished_workers) == 0:
            self.finished.emit(self.results)

    def cancel(self) -> None:
        clean_up()
        self.cancelled = True
        for worker in self.workers:
            if str(worker) not in self.results:
                self.results[str(worker)] = False
        self.finished_workers = []
        self.finished.emit(self.results)
