from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

if TYPE_CHECKING:
    from PySide6.QtGui import QResizeEvent

    from songs_to_youtube.panes.tree.widget_item.data import TreeWidgetItemData


class MetadataTableWidget(QTableWidget):
    def from_data(self, data: TreeWidgetItemData) -> None:
        for key, value in data.to_dict().items():
            self.insertRow(self.rowCount())
            key_item = QTableWidgetItem(key)
            key_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemNeverHasChildren)
            value_item = QTableWidgetItem(str(value))
            value_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemNeverHasChildren)
            self.setItem(self.rowCount() - 1, 0, key_item)
            self.setItem(self.rowCount() - 1, 1, value_item)

    def resizeEvent(self, event: QResizeEvent) -> None:
        for c in range(self.columnCount()):
            self.setColumnWidth(c, event.size().width() // self.columnCount())
