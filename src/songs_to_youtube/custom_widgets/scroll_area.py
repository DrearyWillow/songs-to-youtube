from typing import TYPE_CHECKING

from PySide6.QtWidgets import QScrollArea

from .cover_art_display import CoverArtDisplay

if TYPE_CHECKING:
    from PySide6.QtGui import QResizeEvent


class SettingsScrollArea(QScrollArea):
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if cover_art_display := self.findChild(CoverArtDisplay):
            cover_art_display.scroll_area_width_resized(event.size().width())
