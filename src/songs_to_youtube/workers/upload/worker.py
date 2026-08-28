import logging
import traceback
from typing import ClassVar

from PySide6.QtCore import QObject, Signal
from youtube_up import Metadata as YTMetadata
from youtube_up import YTUploaderSession

from songs_to_youtube.utils.cookies import get_cookie_jar_for_username


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
                last_step: str | None = None

                def callback(step: str, progress: float, file: str = file) -> None:
                    self.on_progress.emit(file, progress)
                    nonlocal last_step
                    if step != last_step:
                        last_step = step
                        self.log_message.emit(self.UPLOAD_STEP_MESSAGES[step], logging.INFO)

                try:
                    self.log_message.emit(str(metadata), logging.DEBUG)
                    self.uploader.upload(file, metadata, callback)
                    success = True
                    self.upload_finished.emit(file, success)
                except Exception:
                    self.log_message.emit(traceback.format_exc(), logging.ERROR)
                    success = False
                    self.upload_finished.emit(file, success)

        except Exception:
            self.log_message.emit(traceback.format_exc(), logging.ERROR)
        finally:
            self.finished.emit()
