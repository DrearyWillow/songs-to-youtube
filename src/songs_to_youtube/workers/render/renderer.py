from typing import Self

from PySide6.QtCore import QThreadPool, Signal

from songs_to_youtube.applogger import applogger
from songs_to_youtube.const import SETTINGS_VALUES
from songs_to_youtube.panes.tree.widget_item.album import AlbumTreeWidgetItem
from songs_to_youtube.panes.tree.widget_item.song import SongTreeWidgetItem
from songs_to_youtube.utils import get_setting
from songs_to_youtube.workers.base_class import WorkerBaseClass
from songs_to_youtube.workers.render.process_handler import clean_up
from songs_to_youtube.workers.render.workers import CombineSongWorker, RenderSongWorker, SongWorker


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


class Renderer(WorkerBaseClass):
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
