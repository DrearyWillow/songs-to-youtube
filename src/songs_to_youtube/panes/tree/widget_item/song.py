import pathlib
import posixpath
from typing import Literal, cast

from PySide6.QtCore import QFileInfo, QStandardPaths
from PySide6.QtGui import QStandardItem, Qt

from songs_to_youtube.const import CustomDataRole, TreeWidgetType
from songs_to_youtube.panes.tree.widget_item.data import TreeWidgetItemData
from songs_to_youtube.utils import resource_path


class SongTreeWidgetItem(QStandardItem):
    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled)
        self.setData(TreeWidgetType.SONG, CustomDataRole.ITEMTYPE)
        info = QFileInfo(file_path)
        self.setData(
            TreeWidgetItemData(
                TreeWidgetType.SONG,
                song_path=file_path,
                song_dir=info.path(),
                song_file=info.fileName(),
            ),
            CustomDataRole.ITEMDATA,
        )
        # set acodec to copy by default,
        # overridden when concatenating
        self.set("audioCodec", "copy")

    def get(self, field: str) -> str:
        return self.data(CustomDataRole.ITEMDATA).get_value(field)

    def set(self, field: str, value: str) -> None:
        self.data(CustomDataRole.ITEMDATA).set_value(field, value)

    def to_dict(self) -> dict[str, str]:
        return self.data(CustomDataRole.ITEMDATA).to_dict()

    def item_type(self) -> Literal[TreeWidgetType.SONG]:
        return self.data(CustomDataRole.ITEMTYPE)

    def get_duration_ms(self) -> float:
        return self.data(CustomDataRole.ITEMDATA).get_duration_ms()

    def before_render(self) -> None:
        self.set("fileOutput", posixpath.join(self.get("fileOutputDir"), self.get("fileOutputName")))
        self.set("songDuration", str(self.get_duration_ms() / 1000))
        command_path = resource_path(posixpath.join("commands", "render", self.get("commandName") + ".command"))
        if not pathlib.Path(command_path).exists():
            appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            command_path = posixpath.join(appdata_path, "commands", "render", self.get("commandName") + ".command")
        try:
            command = pathlib.Path(command_path).read_text(encoding="utf-8").strip()
            self.set("commandString", command)
        except Exception as e:
            msg = f"Could not read command from {command_path}"
            raise OSError(msg) from e

    def before_upload(self) -> None:
        pass

    def get_track_number(self) -> int:
        return self.data(CustomDataRole.ITEMDATA).get_track_number()

    @classmethod
    def from_standard_item(cls, item: QStandardItem) -> SongTreeWidgetItem:
        for name, value in cls.__dict__.items():
            if callable(value) and name != "__init__":
                bound = value.__get__(item)
                setattr(item, name, bound)
        return cast("SongTreeWidgetItem", item)
