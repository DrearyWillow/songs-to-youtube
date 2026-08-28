import pathlib
import posixpath
from collections.abc import Iterator
from typing import Literal, cast

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QStandardItem, Qt

from songs_to_youtube.const import SETTINGS_VALUES, CustomDataRole, TreeWidgetType
from songs_to_youtube.panes.tree.widget_item.data import TreeWidgetItemData
from songs_to_youtube.panes.tree.widget_item.song import SongTreeWidgetItem
from songs_to_youtube.utils import get_setting, resource_path


class AlbumTreeWidgetItem(QStandardItem):
    def __init__(self, dir_path: str, songs: list[SongTreeWidgetItem]) -> None:
        super().__init__()
        self.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
        )
        self.setData(TreeWidgetType.ALBUM, CustomDataRole.ITEMTYPE)

        # order songs by tracknumber if possible
        songs.sort(key=lambda song: song.get_track_number())

        self.setData(
            TreeWidgetItemData(TreeWidgetType.ALBUM, songs, album_dir=dir_path),
            CustomDataRole.ITEMDATA,
        )

        for song in songs:
            self.addChild(song)

    def get(self, field: str) -> str:
        return self.data(CustomDataRole.ITEMDATA).get_value(field)

    def set(self, field: str, value: str) -> None:
        self.data(CustomDataRole.ITEMDATA).set_value(field, value)

    def item_type(self) -> Literal[TreeWidgetType.ALBUM]:
        return self.data(CustomDataRole.ITEMTYPE)

    def addChild(self, item: SongTreeWidgetItem) -> None:
        self.appendRow(item)

    def childCount(self) -> int:
        return self.rowCount()

    def getChildren(self) -> Iterator[SongTreeWidgetItem]:
        for i in range(self.childCount()):
            yield SongTreeWidgetItem.from_standard_item(self.child(i))

    @staticmethod
    def getChildrenFromStandardItem(item: QStandardItem) -> Iterator[QStandardItem]:
        for i in range(item.rowCount()):
            yield item.child(i)

    @classmethod
    def from_standard_item(cls, item: QStandardItem) -> "AlbumTreeWidgetItem":
        for name, value in cls.__dict__.items():
            if callable(value) and name != "__init__":
                bound = value.__get__(item)
                setattr(item, name, bound)
        return cast("AlbumTreeWidgetItem", item)

    def get_duration_ms(self) -> float:
        return sum(song.get_duration_ms() for song in self.getChildren())

    def before_render(self) -> None:
        self.data(CustomDataRole.ITEMDATA).set_value("albumDuration", str(self.get_duration_ms() / 1000))
        self.data(CustomDataRole.ITEMDATA).set_value(
            "fileOutput", posixpath.join(self.get("fileOutputDirAlbum"), self.get("fileOutputNameAlbum"))
        )
        command_path = resource_path(posixpath.join("commands", "concat", self.get("concatCommandName") + ".command"))
        if not pathlib.Path(command_path).exists():
            appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            command_path = posixpath.join(
                appdata_path, "commands", "concat", self.get("concatCommandName") + ".command"
            )
        try:
            command = pathlib.Path(command_path).read_text(encoding="utf-8").strip()
            self.set("concatCommandString", command)
        except Exception as e:
            msg = f"Could not read command from {command_path}"
            raise OSError(msg) from e

        if self.get("albumPlaylist") == SETTINGS_VALUES.AlbumPlaylist.SINGLE:
            # override song audio codec output to 24 bit FLAC
            # so they can be concatenated
            for song in self.getChildren():
                song.set("audioCodec", "flac -sample_fmt s32")

    def before_upload(self) -> None:
        # generate timestamps
        data = self.data(CustomDataRole.ITEMDATA)
        timestamp = 0
        timestamp_str = ""
        for song in self.getChildren():
            format_string = get_setting("timestampFormat")
            # create h/m/s keys
            hours, minutes, seconds = (
                int(timestamp // 3600),
                int((timestamp // 60) % 60),
                int(timestamp) % 60,
            )
            song.set(r"%H", str(hours))
            song.set(r"%M", str(minutes))
            song.set(r"%S", str(seconds))
            song.set(r"%0H", f"{hours:02}")
            song.set(r"%0M", f"{minutes:02}")
            song.set(r"%0S", f"{seconds:02}")
            song.set("timestamp", format_string)
            timestamp_str += song.get("timestamp") + "\n"
            timestamp += song.get_duration_ms() / 1000
        data.set_value("timestamps", timestamp_str)
        data.update_fields()
