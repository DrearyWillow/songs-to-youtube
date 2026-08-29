from typing import TYPE_CHECKING

from songs_to_youtube.applogger import applogger
from songs_to_youtube.panes.progress.bar import WorkerProgressBar
from songs_to_youtube.panes.progress.view import ProgressPaneView

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from songs_to_youtube.workers.base_class import WorkerBaseClass
    from songs_to_youtube.workers.render.renderer import Renderer
    from songs_to_youtube.workers.upload.uploader import Uploader


class ProgressPanePresenter:
    def __init__(self, parent: QWidget | None = None) -> None:
        self.workers: dict[str, WorkerProgressBar] = {}
        self.view = ProgressPaneView(parent)
        self.view.scroll_area_visible(visible=False)

    def init_worker_progress(self, worker_name: str) -> None:
        progress = WorkerProgressBar(worker_name, self.view)
        self.workers[worker_name] = progress
        self.view.add_progress_widget(progress)

    def worker_progress(self, worker_name: str, progress: int) -> None:
        self.view.scroll_area_visible(visible=True)
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

        if worker := self.workers.pop(worker_name, None):
            worker.setVisible(False)
            self.view.remove_progress_widget(worker)

    def connect_workers(self, obj: WorkerBaseClass, obj_type: str) -> None:
        def worker_done_intermediate(worker_name: str, *, success: bool) -> None:
            return self.worker_done(worker_name, obj_type, success=success)

        obj.worker_progress.connect(self.worker_progress)
        obj.worker_error.connect(self.worker_error)
        obj.worker_done.connect(worker_done_intermediate)
        obj.finished.connect(lambda: self.view.scroll_area_visible(visible=False))

    def on_render_start(self, renderer: Renderer) -> None:
        self.connect_workers(renderer, "rendering")

    def on_upload_start(self, uploader: Uploader) -> None:
        self.connect_workers(uploader, "uploading")
