import os
from collections.abc import Iterable, Iterator
from typing import cast

from PySide6 import QtCore
from PySide6.QtCore import (
    QFileInfo,
    QItemSelection,
    QItemSelectionModel,
    QItemSelectionRange,
    QMimeData,
    QModelIndex,
    QPoint,
)
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QKeySequence, QShortcut, QStandardItemModel, Qt
from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QMenu, QTableWidget, QTreeView, QWidget

from songs_to_youtube.applogger import applogger
from songs_to_youtube.components.tree.tree_widget_item import AlbumTreeWidgetItem, SongTreeWidgetItem
from songs_to_youtube.const import SETTINGS_VALUES, CustomDataRole, TreeWidgetType
from songs_to_youtube.dialogs.metadata.metadata_table_widget import MetadataTableWidget
from songs_to_youtube.utils import (
    file_is_audio,
    files_in_directory,
    files_in_directory_and_subdirectories,
    get_setting,
    get_short_path_name,
    load_ui,
)
from songs_to_youtube.workers.render import Renderer
from songs_to_youtube.workers.uploader import Uploader


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


class MetadataUI(QTableWidget):
    tableWidget: MetadataTableWidget


class SongTreeWidget(QTreeView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setModel(SongTreeModel())
        self.setSelectionModel(SongTreeSelectionModel(self.model()))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        self.init_shortcuts()

    def model(self) -> SongTreeModel:
        return cast("SongTreeModel", super().model())

    def init_shortcuts(self) -> None:
        self.del_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Delete), self)
        self.del_shortcut.activated.connect(self.remove_selected_items)

    @staticmethod
    def _create_album_item(dir_path: str, songs: list[SongTreeWidgetItem]) -> AlbumTreeWidgetItem:
        return AlbumTreeWidgetItem(dir_path, songs)

    @staticmethod
    def _create_song_item(file_path: str) -> SongTreeWidgetItem:
        return SongTreeWidgetItem(file_path)

    def _get_all_items(self) -> Iterator[AlbumTreeWidgetItem | SongTreeWidgetItem]:
        for row in range(self.model().rowCount()):
            item = self.model().item(row)
            item_type = item.data(CustomDataRole.ITEMTYPE)
            if item_type == TreeWidgetType.ALBUM:
                yield AlbumTreeWidgetItem.from_standard_item(item)
            elif item_type == TreeWidgetType.SONG:
                yield SongTreeWidgetItem.from_standard_item(item)

    def _get_all_items_flat(self) -> Iterator[AlbumTreeWidgetItem | SongTreeWidgetItem]:
        for item in self._get_all_items():
            yield item
            if isinstance(item, AlbumTreeWidgetItem):
                yield from item.getChildren()

    def remove_by_file_paths(self, paths: Iterable[str], *, uploaded: bool = True) -> None:
        """Remove items from widget with output paths given by paths;
        if uploaded is False, only remove items which are not going
        to be uploaded (render-only)"""
        for item in list(self._get_all_items_flat())[::-1]:
            if (item.get("fileOutput") in paths and uploaded) or (
                item.get("uploadYouTube") == SETTINGS_VALUES.CheckBox.UNCHECKED
            ):
                self.model().removeRow(item.row(), item.index().parent())

        # if all children of an album are removed,
        # remove the album as well
        for item in list(self._get_all_items())[::-1]:
            if isinstance(item, AlbumTreeWidgetItem) and item.childCount() == 0:
                self.model().removeRow(item.row(), item.index().parent())

    def remove_all(self) -> None:
        if self.model().hasChildren():
            self.model().removeRows(0, self.model().rowCount())

    def addTopLevelItem(self, item: AlbumTreeWidgetItem | SongTreeWidgetItem) -> None:
        self.model().appendRow(item)

    def remove_selected_items(self) -> None:
        while len(self.selectedIndexes()) > 0:
            index = self.selectedIndexes()[0]
            index.model().removeRow(index.row(), index.parent())

    def show_metadata_menu(self, index: QModelIndex) -> None:
        self.metadata_dialog = cast("MetadataUI", load_ui("metadata.ui", (MetadataTableWidget,)))
        self.metadata_dialog.tableWidget.from_data(index.data(CustomDataRole.ITEMDATA))
        self.metadata_dialog.show()

    def on_context_menu(self, pos: QPoint) -> None:
        index = self.indexAt(pos)
        menu = QMenu(self)

        meta_action = menu.addAction("View metadata")
        meta_action.triggered.connect(lambda _=False, index=index: self.show_metadata_menu(index))

        remove_action = menu.addAction("Remove")
        remove_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Delete))
        remove_action.triggered.connect(self.remove_selected_items)

        menu.popup(self.viewport().mapToGlobal(pos))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.source() is self or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.source() is self:
            event.acceptProposedAction()
        elif event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.source():
            super().dropEvent(event)
        else:
            for url in event.mimeData().urls():
                info = QFileInfo(url.toLocalFile())
                if not info.isReadable():
                    applogger.warning("File %s is not readable", info.filePath())
                    continue
                if info.isDir():
                    if get_setting("dragAndDropBehavior") == SETTINGS_VALUES.DragAndDrop.ALBUM_MODE:
                        self.addAlbum(url.toLocalFile())
                    else:
                        for file_path in files_in_directory_and_subdirectories(info.filePath()):
                            self.addSong(file_path)
                else:
                    self.addSong(info.filePath())

    def addAlbum(self, dir_path: str) -> None:
        songs: list[SongTreeWidgetItem] = []
        max_windows_filepath = 255
        for file_path in files_in_directory(dir_path):
            path = file_path
            if os.name == "nt" and len(path) > max_windows_filepath:
                path = get_short_path_name(path)
            info = QFileInfo(path)
            if not info.isReadable():
                applogger.warning("File %s is not readable", path)
                continue
            if info.isDir():
                self.addAlbum(path)
            elif file_is_audio(path):
                item = self._create_song_item(path)
                item.setText(info.fileName())
                songs.append(item)
        if len(songs) > 0:
            album_item = self._create_album_item(dir_path, songs)
            album_item.setText(dir_path)
            self.addTopLevelItem(album_item)

    def addSong(self, path: str) -> None:
        max_windows_filepath = 255
        if os.name == "nt" and len(path) > max_windows_filepath:
            path = get_short_path_name(path)
        if not file_is_audio(path):
            applogger.info("File %s is not audio", path)
            return
        item = self._create_song_item(path)
        item.setText(QFileInfo(path).fileName())
        self.addTopLevelItem(item)

    def get_renderer(self) -> Renderer:
        renderer = Renderer()
        for item in self._get_all_items():
            if isinstance(item, AlbumTreeWidgetItem):
                renderer.add_render_album_job(item)
            else:
                renderer.add_render_song_job(item)
        return renderer

    def get_uploader(self, render_results: dict[str, bool]) -> Uploader:
        uploader = Uploader(render_results)
        for row in range(self.model().rowCount()):
            item = self.model().item(row)
            if item.data(CustomDataRole.ITEMTYPE) == TreeWidgetType.ALBUM:
                item = AlbumTreeWidgetItem.from_standard_item(item)
                uploader.add_upload_album_job(item)
            elif item.data(CustomDataRole.ITEMTYPE) == TreeWidgetType.SONG:
                item = SongTreeWidgetItem.from_standard_item(item)
                uploader.add_upload_song_job(item)
        return uploader
