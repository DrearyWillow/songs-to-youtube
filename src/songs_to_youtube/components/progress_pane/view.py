from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from songs_to_youtube.components.progress_pane.bar import WorkerProgressBar
from songs_to_youtube.utils import find_ancestor


class ProgressPaneView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area_visible(visible=False)

    def add_progress_widget(self, progress_bar: WorkerProgressBar) -> None:
        self._layout.addWidget(progress_bar)

    def remove_progress_widget(self, progress_bar: WorkerProgressBar) -> None:
        self._layout.removeWidget(progress_bar)

    def scroll_area_visible(self, *, visible: bool) -> None:
        scroll_area = find_ancestor(self, "QScrollArea")
        if isinstance(scroll_area, QScrollArea):
            scroll_area.setVisible(visible)
