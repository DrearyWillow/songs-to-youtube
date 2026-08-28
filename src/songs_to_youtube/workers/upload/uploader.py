from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal

from songs_to_youtube.applogger import applogger
from songs_to_youtube.const import SETTINGS_VALUES
from songs_to_youtube.panes.tree.widget_item.album import AlbumTreeWidgetItem
from songs_to_youtube.panes.tree.widget_item.song import SongTreeWidgetItem
from songs_to_youtube.utils import get_setting
from songs_to_youtube.workers.base_class import WorkerBaseClass
from songs_to_youtube.workers.upload.metadata import get_album_metadata, get_song_metadata
from songs_to_youtube.workers.upload.worker import UploadWorker

if TYPE_CHECKING:
    from youtube_up import Metadata as YTMetadata


class Uploader(WorkerBaseClass):
    # dict of worker name and worker success
    finished = Signal(dict[str, bool])

    # worker name, worker progress (percentage)
    worker_progress = Signal(str, int)

    # not used
    worker_error = Signal(str, str)

    # worker name
    worker_done = Signal(str, bool)

    def __init__(self, render_results: dict[str, bool]) -> None:
        super().__init__()
        self.uploading = False
        self.jobs: list[tuple[str, YTMetadata]] = []  # file path and metadata
        self.results: dict[str, bool] = {}
        self.render_results = render_results
        self.cancelled = False
        self.worker = None
        self._thread: QThread | None = None

    def add_upload_album_job(self, album: AlbumTreeWidgetItem) -> None:
        if album.childCount() == 0:
            return

        if album.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.SINGLE:
            if album.get("uploadYouTube") != SETTINGS_VALUES.CheckBox.CHECKED:
                return

            file = album.get("fileOutput")
            if not self.render_results.get(file):
                return

            self.jobs.append((file, get_album_metadata(album)))

        elif album.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.MULTIPLE:
            for song in album.getChildren():
                self.add_upload_song_job(song)

    def add_upload_song_job(self, song: SongTreeWidgetItem) -> None:
        if song.get("uploadYouTube") != SETTINGS_VALUES.CheckBox.CHECKED:
            return

        file = song.get("fileOutput")
        if not self.render_results.get(file):
            return

        if any(job_file == file for job_file, _ in self.jobs):
            applogger.error(f"Ignoring duplicate job {file}")
        else:
            self.jobs.append((file, get_song_metadata(song)))

    def upload_finished(self, file_path: str, *, success: bool) -> None:
        self.results[file_path] = success
        self.worker_done.emit(file_path, success)

    def on_done_uploading(self, file_path: str, *, success: bool) -> None:
        if not self.cancelled:
            self.uploading = False
            self.results[file_path] = success

    def cancel(self) -> None:
        self.cancelled = True
        for file, _ in self.jobs:
            if file not in self.results:
                self.results[file] = False
        self.finished.emit(self.results)

    def is_uploading(self) -> bool:
        return self.uploading

    def worker_finished(self) -> None:
        if worker := self.worker:
            worker.deleteLater()
        if thread := self._thread:
            thread.quit()
        self.finished.emit(self.results)

    def log(self, message: str, level: int) -> None:
        if not self.cancelled:
            applogger.log(level, message)

    def upload(self) -> None:
        self.results = {file: False for file, _ in self.jobs}
        if len(self.jobs) == 0:
            self.finished.emit(self.results)
            return
        self._thread = QThread()
        username = get_setting("username")
        if not username:
            raise ValueError("No user selected to upload to. Add a user at File > Settings > Add new user")
        self.worker = UploadWorker(username, self.jobs)
        self.worker.moveToThread(self._thread)
        self._thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_finished)
        self._thread.finished.connect(self._thread.deleteLater)
        self.worker.log_message.connect(self.log)
        self.worker.on_progress.connect(self.worker_progress.emit)
        self.worker.upload_finished.connect(self.upload_finished)
        self._thread.start()
