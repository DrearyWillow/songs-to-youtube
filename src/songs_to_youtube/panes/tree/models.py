

from PySide6 import QtCore
from PySide6.QtCore import QItemSelection, QItemSelectionModel, QItemSelectionRange, QMimeData, QModelIndex
from PySide6.QtGui import QStandardItemModel, Qt

from songs_to_youtube.const import CustomDataRole, TreeWidgetType


class SongTreeModel(QStandardItemModel):
    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex,
    ) -> bool:
        # If album dropped onto another album, don't insert
        if parent.isValid():
            dummy_model = QStandardItemModel()
            dummy_model.dropMimeData(data, action, 0, 0, QModelIndex())
            indexes: list[QModelIndex] = []
            for r in range(dummy_model.rowCount()):
                for c in range(dummy_model.columnCount()):
                    index = dummy_model.index(r, c)
                    # QStandardItemModel doesn't recognize our items as our custom classes
                    # so we have to treat them as QStandardItems
                    item = dummy_model.item(r, c)
                    if item.data(CustomDataRole.ITEMTYPE) == TreeWidgetType.ALBUM:
                        pass
                    elif item.data(CustomDataRole.ITEMTYPE) == TreeWidgetType.SONG:
                        indexes.append(index)
            data = dummy_model.mimeData(indexes)
        return super().dropMimeData(data, action, row, column, parent)


class SongTreeSelectionModel(QItemSelectionModel):
    def _going_to_select_item(
        self, index: QtCore.QModelIndex | QtCore.QPersistentModelIndex, command: QItemSelectionModel.SelectionFlag
    ) -> bool:
        if command & QItemSelectionModel.SelectionFlag.Select:
            return True
        return bool(command & QItemSelectionModel.SelectionFlag.Toggle and not self.isSelected(index))

    def select(
        self,
        selected: QtCore.QModelIndex | QtCore.QPersistentModelIndex | QItemSelection,
        command: QItemSelectionModel.SelectionFlag,
        /,
    ) -> None:
        # If one of the selected items is an album,
        # deselect all song items to make sure
        # we only edit items of the same type
        # at the same time
        if isinstance(selected, QModelIndex):
            # turn single selected index into a QItemSelection
            # so we only have to deal with one type
            selected = QItemSelection(selected, selected)

        # check if after this selection action
        # we would have an album selected
        # this will emit selectionChanged
        super().select(selected, command)
        album_selected = False
        for index in self.selection().indexes():
            if index.data(CustomDataRole.ITEMTYPE) == TreeWidgetType.ALBUM:
                album_selected = True
                break

        if album_selected:
            deselect = QItemSelection()
            # deselect all song items
            for index in self.selection().indexes():
                if index.data(CustomDataRole.ITEMTYPE) == TreeWidgetType.SONG:
                    deselect.append(QItemSelectionRange(index, index))

            if not deselect.isEmpty():
                super().select(deselect, QItemSelectionModel.SelectionFlag.Deselect)