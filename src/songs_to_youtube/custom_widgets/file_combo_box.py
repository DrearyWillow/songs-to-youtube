import pathlib
import posixpath

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QComboBox, QWidget

from songs_to_youtube.utils import resource_path


class FileComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dirs: list[str] = []
        self.objectNameChanged.connect(self.set_dir)

    def set_dir(self, object_name: str) -> None:
        # take screenshot and quit
        appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        commands_dir = posixpath.join(appdata_path, "commands")
        pathlib.Path(commands_dir).mkdir(exist_ok=True, parents=True)
        if object_name == "commandName":
            render_dir = posixpath.join(commands_dir, "render")
            pathlib.Path(render_dir).mkdir(exist_ok=True, parents=True)
            self.dirs = [resource_path("commands/render"), render_dir]
        elif object_name == "concatCommandName":
            concat_dir = posixpath.join(commands_dir, "concat")
            pathlib.Path(concat_dir).mkdir(exist_ok=True, parents=True)
            self.dirs = [resource_path("commands/concat"), concat_dir]
        else:
            msg = f"ComboBox has name {self.objectName()}"
            raise ValueError(msg)
        self.reload()

    def reload(self) -> None:
        commands: set[str] = set()
        for d in self.dirs:
            for file in pathlib.Path.iterdir(pathlib.Path(d)):
                if file.is_file() and str(file).endswith(".command"):
                    name = str(file)[: -len(".command")]
                    commands.add(name)
                    if self.findText(name) == -1:
                        self.addItem(name, name)
        for i in range(self.count()):
            if self.itemText(i) not in commands:
                self.removeItem(i)
