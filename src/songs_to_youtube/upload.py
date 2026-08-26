import glob
import json
import logging
import posixpath
import time
import traceback
from http.cookiejar import Cookie, FileCookieJar, MozillaCookieJar
from typing import ClassVar

from _typeshed import SupportsRead
from PySide6.QtCore import QObject, QThread, Signal
from youtube_up import Metadata as YTMetadata
from youtube_up import Playlist as YTPlaylist
from youtube_up import PrivacyEnum, YTUploaderSession

from songs_to_youtube.field import SETTINGS_VALUES
from songs_to_youtube.log import applogger
from songs_to_youtube.progress_worker import BaseProgressWorker
from songs_to_youtube.settings import get_setting
from songs_to_youtube.song_tree_widget_item import AlbumTreeWidgetItem, SongTreeWidgetItem
from songs_to_youtube.utils import YouTubeLogin


def make_metadata_safe(metadata: YTMetadata) -> YTMetadata:
    metadata.title = metadata.title[:100]
    metadata.description = metadata.description[:5000]
    metadata.title = metadata.title.replace("<", "＜").replace(">", "＞")
    metadata.description = metadata.description.replace("<", "＜").replace(">", "＞")
    return metadata


class JSONFileCookieJar(FileCookieJar):
    def _really_load(
        self, f: SupportsRead[str | bytes], filename: str | None, ignore_discard: bool, ignore_expires: bool
    ) -> None:
        now = int(time.time())
        cookies = json.load(f)
        for cookie in cookies:
            rest = {}
            if cookie.get("httpOnly"):
                rest["HTTPOnly"] = ""
            if isinstance(cookie["secure"], str):
                cookie["secure"] = cookie["secure"] == "TRUE"
            c = Cookie(
                0,
                cookie["name"],
                cookie["value"],
                None,
                False,
                cookie["domain"],
                True,
                cookie["domain"].startswith("."),
                cookie["path"],
                True,
                cookie["secure"],
                cookie["expires"] or None,
                False,
                None,
                None,
                rest,
            )
            if not ignore_discard and c.discard:
                continue
            if not ignore_expires and c.is_expired(now):
                continue
            self.set_cookie(c)

    def save(self, filename: str | None = None, ignore_discard: bool = False, ignore_expires: bool = False) -> None:
        now = int(time.time())
        cookies = []
        for cookie in self:
            domain = cookie.domain
            if not ignore_discard and cookie.discard:
                continue
            if not ignore_expires and cookie.is_expired(now):
                continue
            secure = cookie.secure
            if cookie.expires is not None:
                expires = str(cookie.expires)
            else:
                expires = ""
            if cookie.value is None:
                name = ""
                value = cookie.name
            else:
                name = cookie.name
                value = cookie.value
            httpOnly = False
            if cookie.has_nonstandard_attr("HTTPOnly"):
                httpOnly = True
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": cookie.path,
                    "expires": expires,
                    "httpOnly": httpOnly,
                    "secure": secure,
                }
            )

        if filename is None and self.filename is not None:
            filename = self.filename

        if filename is not None:
            with open(filename, "w") as f:
                json.dump(cookies, f)


def get_cookie_jar_for_username(username: str) -> FileCookieJar:
    cookie_dir = YouTubeLogin.get_cookie_path_from_username(username)
    txt_cookie_paths = glob.glob(posixpath.join(cookie_dir, "*.txt"))
    json_cookie_paths = glob.glob(posixpath.join(cookie_dir, "*.json"))
    if txt_cookie_paths:
        return MozillaCookieJar(txt_cookie_paths[0])
    elif json_cookie_paths:
        return JSONFileCookieJar(json_cookie_paths[0])
    else:
        raise FileNotFoundError(f"No cookie files matching *.txt or *.json found in {cookie_dir}")


class UploadWorker(QObject):
    upload_finished = Signal(str, bool)  # file_path, success
    log_message = Signal(str, int)  # message, loglevel
    on_progress = Signal(str, int)  # job name, percent done
    finished = Signal()

    UPLOAD_STEP_MESSAGES: ClassVar[dict[str, str]] = {
        "start": "Starting upload",
        "get_session_data": "Getting session data",
        "get_upload_url": "Getting upload URL",
        "upload_video": "Uploading video file",
        "get_session_token": "Getting session token",
        "create_video": "Creating video",
        "upload_thumbnail": "Uploading thumbnail",
        "finish": "Upload finished",
    }

    def __init__(self, username: str, jobs: list[tuple[str, YTMetadata]]) -> None:
        super().__init__()
        self.jobs = jobs
        self.username = username

    def run(self) -> None:
        try:
            cj = get_cookie_jar_for_username(self.username)
            self.uploader = YTUploaderSession(cj)
            for file, metadata in self.jobs:
                last_step = None

                def callback(step, progress, file=file):
                    self.on_progress.emit(file, progress)
                    nonlocal last_step
                    if step != last_step:
                        last_step = step
                        self.log_message.emit(self.UPLOAD_STEP_MESSAGES[step], logging.INFO)

                try:
                    self.log_message.emit(str(metadata), logging.DEBUG)
                    self.uploader.upload(file, metadata, callback)
                    self.upload_finished.emit(file, True)
                except Exception:
                    self.log_message.emit(traceback.format_exc(), logging.ERROR)
                    self.upload_finished.emit(file, False)

        except Exception:
            self.log_message.emit(traceback.format_exc(), logging.ERROR)
        finally:
            self.finished.emit()


class Uploader(BaseProgressWorker):
    # dict of worker name and worker success
    finished = Signal(dict[str, bool])

    # worker name, worker progress (percentage)
    worker_progress = Signal(str, int)

    # not used
    worker_error = Signal(str, str)

    # worker name
    worker_done = Signal(str, bool)

    def __init__(self, render_results: dict[str, bool], *args) -> None:
        super().__init__()
        self.uploading = False
        self.jobs: list[tuple[str, YTMetadata]] = []  # file path and metadata
        self.results = {}
        self.render_results = render_results
        self.cancelled = False
        self.worker = None
        self._thread: QThread | None = None

    def upload_finished(self, file_path, success) -> None:
        self.results[file_path] = success
        self.worker_done.emit(file_path, success)

    def on_done_uploading(self, file_path, success) -> None:
        if not self.cancelled:
            self.uploading = False
            self.results[file_path] = success

    def cancel(self) -> None:
        self.cancelled = True
        for file, _ in self.jobs:
            if file not in self.results:
                self.results[file] = False
        self.finished.emit(self.results)

    def add_upload_album_job(self, album: AlbumTreeWidgetItem) -> None:
        if album.childCount() == 0:
            return
        if album.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.SINGLE:
            if album.get("uploadYouTube") == SETTINGS_VALUES.CheckBox.CHECKED:
                file = album.get("fileOutput")
                if file in self.render_results and self.render_results[file]:
                    album.before_upload()
                    privacy = album.get("videoVisibilityAlbum")
                    notify_subs = album.get("notifySubsAlbum") == SETTINGS_VALUES.CheckBox.CHECKED
                    tags = album.get("videoTagsAlbum").split(",") if album.get("videoTagsAlbum") else []
                    metadata = make_metadata_safe(
                        YTMetadata(
                            album.get("videoTitleAlbum"),
                            album.get("videoDescriptionAlbum"),
                            PrivacyEnum(privacy),
                            False,
                            tuple(tags),
                            publish_to_feed=notify_subs,
                        )
                    )
                    self.jobs.append((file, metadata))
        elif album.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.MULTIPLE:
            for song in album.getChildren():
                if isinstance(song, SongTreeWidgetItem):
                    self.add_upload_song_job(song)

    def add_upload_song_job(self, song: SongTreeWidgetItem) -> None:
        if song.get("uploadYouTube") == SETTINGS_VALUES.CheckBox.CHECKED:
            file = song.get("fileOutput")
            if file in self.render_results and self.render_results[file]:
                song.before_upload()
                privacy = song.get("videoVisibility")
                notify_subs = song.get("notifySubs") == SETTINGS_VALUES.CheckBox.CHECKED
                tags = song.get("videoTags").split(",") if song.get("videoTags") else []
                playlist_names = song.get("playlistName").split("\n")
                playlists = [
                    YTPlaylist(
                        name,
                        privacy=PrivacyEnum(privacy),
                        create_if_title_exists=False,
                        create_if_title_doesnt_exist=True,
                    )
                    for name in playlist_names
                    if name
                ]
                metadata = make_metadata_safe(
                    YTMetadata(
                        song.get("videoTitle"),
                        song.get("videoDescription"),
                        PrivacyEnum(privacy),
                        False,
                        tuple(tags),
                        playlists=playlists,
                        publish_to_feed=notify_subs,
                    )
                )
                if any(job_file == file for job_file, _ in self.jobs):
                    applogger.error(f"Ignoring duplicate job {file}")
                else:
                    self.jobs.append((file, metadata))

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
        self.worker.on_progress.connect(lambda worker_name, progress: self.worker_progress.emit(worker_name, progress))
        self.worker.upload_finished.connect(self.upload_finished)
        self._thread.start()
