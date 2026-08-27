from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget

from songs_to_youtube.log import applogger
from songs_to_youtube.progress_worker import BaseProgressWorker
from songs_to_youtube.render import Renderer
from songs_to_youtube.upload import Uploader
from songs_to_youtube.utils import find_ancestor


class WorkerProgress(QWidget):
    def __init__(self, worker_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        if not (layout := self.layout()):
            return
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.label = QLabel(self)
        self.label.setText(worker_name.replace("\\", "/").split("/")[-1] + ":")
        self.progress = QProgressBar(self)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.progress.setValue(0)


class ProgressWindow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        self.workers: dict[str, WorkerProgress] = {}

        super().__init__(parent)

        self.setLayout(QVBoxLayout())
        if layout := self.layout():
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_area_visible(visible=False)

    def init_worker_progress(self, worker_name: str) -> None:
        progress = WorkerProgress(worker_name, self)
        self.workers[worker_name] = progress
        if layout := self.layout():
            layout.addWidget(progress)

    def worker_progress(self, worker_name: str, progress: int) -> None:
        self._scroll_area_visible(visible=True)
        if worker_name not in self.workers:
            self.init_worker_progress(worker_name)
        worker = self.workers[worker_name]
        worker.progress.setValue(progress)

    def worker_error(self, worker_name: str, error: str) -> None:
        if worker_name not in self.workers:
            self.init_worker_progress(worker_name)
        applogger.error("%s - %s", worker_name, error)

    def worker_done(self, worker_name: str, obj_type: str, *, success: bool) -> None:
        if success:
            applogger.success(f"{worker_name} - Done {obj_type}")
        else:
            applogger.error(f"{worker_name} - Error while {obj_type}")
        worker = self.workers.pop(worker_name, None)
        if worker:
            worker.setVisible(False)
            if layout := self.layout():
                layout.removeWidget(worker)

    def connect_workers(self, obj: BaseProgressWorker, obj_type: str) -> None:
        def worker_done_intermediate(worker_name: str, *, success: bool) -> None:
            return self.worker_done(worker_name, obj_type, success=success)
        obj.worker_progress.connect(self.worker_progress)
        obj.worker_error.connect(self.worker_error)
        obj.worker_done.connect(worker_done_intermediate)
        obj.finished.connect(lambda: self._scroll_area_visible(visible=False))

    def on_render_start(self, renderer: Renderer) -> None:
        self.connect_workers(renderer, "rendering")

    def on_upload_start(self, uploader: Uploader) -> None:
        self.connect_workers(uploader, "uploading")

    def _scroll_area_visible(self, *, visible: bool) -> None:
        scroll_area = find_ancestor(self, "QScrollArea")
        if isinstance(scroll_area, QScrollArea):
            scroll_area.setVisible(visible)
