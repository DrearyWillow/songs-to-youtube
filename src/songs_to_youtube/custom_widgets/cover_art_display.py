import typing

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from songs_to_youtube.utils import find_ancestor, get_image_from_mimedata, mimedata_has_image
from songs_to_youtube.utils.misc import APPLICATION_IMAGES, SETTINGS_VALUES


class CoverArtDisplay(QLabel):
    imageChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        # The full artwork pixmap, so we can scale down
        # as the scroll area gets resized
        self.full_pixmap = None

        # Path to original image file
        self.image_path = ""

        super().__init__(parent)
        self.setAcceptDrops(True)

    def get(self) -> str:
        if self.image_path == SETTINGS_VALUES.MULTIPLE_VALUES_IMG:
            return SETTINGS_VALUES.MULTIPLE_VALUES
        return self.image_path

    def set(self, path: str) -> None:
        if path == SETTINGS_VALUES.MULTIPLE_VALUES:
            path = SETTINGS_VALUES.MULTIPLE_VALUES_IMG
        if path == self.image_path:
            return
        if self.set_pixmap(QPixmap(path)):
            self.image_path = path
            self.imageChanged.emit(path)
        else:
            # set to default image
            path = APPLICATION_IMAGES[":/image/default.jpg"]
            self.set_pixmap(QPixmap(path))
            self.image_path = path
            self.imageChanged.emit(path)

    def _get_scroll_area_width(self) -> int | None:
        scroll_area = find_ancestor(self, "SettingsScrollArea")
        if isinstance(scroll_area, QScrollArea):
            return scroll_area.size().width()
        return None

    def set_pixmap(self, pixmap: QPixmap) -> bool:
        if pixmap.isNull():
            return False

        self.full_pixmap = pixmap
        if scroll_area_width := self._get_scroll_area_width():
            width = min(scroll_area_width / 2, pixmap.size().width())
            super().setPixmap(pixmap.scaledToWidth(int(width)))
            return True
        return False

    def scroll_area_width_resized(self, width: float) -> None:
        if self.full_pixmap and not self.full_pixmap.isNull():
            width = min(width / 2, self.full_pixmap.size().width())
            scaled = self.full_pixmap.scaledToWidth(int(width))
            super().setPixmap(scaled)

    @typing.override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.source() is None and mimedata_has_image(event.mimeData()):  # pyright: ignore[reportUnnecessaryComparison]
            event.acceptProposedAction()
        else:
            event.ignore()

    @typing.override
    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.source() is None and mimedata_has_image(event.mimeData()):  # pyright: ignore[reportUnnecessaryComparison]
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if (path := get_image_from_mimedata(event.mimeData())) is not None:
            self.set(path)
