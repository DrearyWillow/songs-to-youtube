import pathlib
import posixpath
import shutil
import typing
from typing import cast

from PySide6.QtCore import QSettings, QStandardPaths, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QPixmap, QResizeEvent, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QWidget,
)

from songs_to_youtube.const import ORGANIZATION, SETTINGS_FILENAME, SUPPORTED_IMAGE_FILTER
from songs_to_youtube.field import APPLICATION_IMAGES, SETTINGS_VALUES, checkstate_to_int, get_all_fields
from songs_to_youtube.utils import (
    YouTubeLogin,
    find_ancestor,
    find_child_text,
    get_all_children,
    get_image_from_mimedata,
    load_ui,
    mimedata_has_image,
    resource_path,
)


def get_settings() -> QSettings:
    """Returns the QSettings for this application"""
    settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORGANIZATION, SETTINGS_FILENAME)
    # for some reason this doesn't work when the settings are first initialized so we do this
    return QSettings(settings.fileName(), QSettings.Format.IniFormat)


def get_setting(setting: str, settings: QSettings | None = None) -> str:
    """Returns the value of the given setting"""
    if settings is None:
        settings = get_settings()
    if not settings.contains(setting):
        # try to load from default settings
        defaults = QSettings(resource_path("config/default.ini"), QSettings.Format.IniFormat)
        if not defaults.contains(setting):
            msg = f"Setting {setting} does not exist"
            raise ValueError(msg)
        return defaults.value(setting)
    return settings.value(setting)


class FileComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dirs = []
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


class SettingCheckBox(QCheckBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTristate()

    def nextCheckState(self) -> None:
        # don't let user select inbetween state
        if self.checkState() == Qt.CheckState.PartiallyChecked:
            self.setCheckState(Qt.CheckState.Checked)
        else:
            self.setChecked(not self.isChecked())
        self.stateChanged.emit(checkstate_to_int(self.checkState()))


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


class SettingsScrollArea(QScrollArea):
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if cover_art_display := self.findChild(CoverArtDisplay):
            cover_art_display.scroll_area_width_resized(event.size().width())


class AddUserWindowUI(QDialog):
    buttonBox: QDialogButtonBox
    cookiesButton: QPushButton
    cookiesFile: QLineEdit
    username: QLineEdit


class AddUserWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = cast("AddUserWindowUI", load_ui("adduser.ui"))
        self.connect_actions()

    def connect_actions(self) -> None:
        self.ui.buttonBox.accepted.connect(self.save_user)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.cookiesButton.clicked.connect(self.open_cookies)

    def open_cookies(self) -> None:
        cookie_file = QFileDialog.getOpenFileName(
            self, "Select cookies.txt or json file", filter="Cookies (*.txt *.json)"
        )[0]
        if cookie_file:
            self.ui.cookiesFile.setText(cookie_file)

    def save_user(self) -> None:
        cookie_folder = YouTubeLogin.get_cookie_path_from_username(self.ui.username.text())
        pathlib.Path(cookie_folder).mkdir(exist_ok=True, parents=True)
        cookie_file = self.ui.cookiesFile.text()
        if cookie_file.endswith("json"):
            cookie_file = posixpath.join(cookie_folder, "youtube.com.json")
        else:
            cookie_file = posixpath.join(cookie_folder, "cookies.txt")
        shutil.copyfile(self.ui.cookiesFile.text(), cookie_file)

    def show(self) -> None:
        self.ui.show()


class SettingsWindowUI(QDialog):
    buttonBox: QDialogButtonBox
    username: QComboBox
    coverArt: CoverArtDisplay
    coverArtButton: QPushButton
    addNewUserButton: QPushButton
    removeUserButton: QPushButton


class SettingsWindow(QDialog):
    settings_changed = Signal()

    SAVE_PRESET_TEXT = "Save preset"
    LOAD_PRESET_TEXT = "Load preset"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ui = cast(
            "SettingsWindowUI",
            load_ui(
                "settingswindow.ui",
                (CoverArtDisplay, SettingCheckBox, SettingsScrollArea, FileComboBox),
            ),
        )
        # rename default buttons
        self.ui.buttonBox.addButton(SettingsWindow.SAVE_PRESET_TEXT, QDialogButtonBox.ButtonRole.ApplyRole)
        self.ui.buttonBox.addButton(SettingsWindow.LOAD_PRESET_TEXT, QDialogButtonBox.ButtonRole.ApplyRole)
        SettingsWindow.init_combo_boxes(self.ui)
        self.connect_actions()
        self.load_settings()

    def add_new_user(self) -> None:
        self.msg_box = AddUserWindow()
        self.msg_box.ui.buttonBox.accepted.connect(self.reload_users)
        self.msg_box.show()

    def remove_user(self) -> None:
        if self.ui.username.currentText():
            cookie_folder = YouTubeLogin.get_cookie_path_from_username(self.ui.username.currentText())
            shutil.rmtree(cookie_folder)
            self.ui.username.removeItem(self.ui.username.currentIndex())

    def save_preset(self) -> None:
        presets_dir = resource_path("config")
        if not pathlib.Path(presets_dir).exists():
            pathlib.Path(presets_dir).mkdir(parents=True)
        file = QFileDialog.getSaveFileName(
            self,
            SettingsWindow.SAVE_PRESET_TEXT,
            presets_dir,
            "Configuration files (*.ini)",
        )[0]
        if file:
            settings = QSettings(file, QSettings.Format.IniFormat)
            self.save_settings_from_fields(settings)

    def load_preset(self) -> None:
        presets_dir = resource_path("config")
        if not pathlib.Path(presets_dir).exists():
            pathlib.Path(presets_dir).mkdir(parents=True)
        file = QFileDialog.getOpenFileName(
            self,
            SettingsWindow.LOAD_PRESET_TEXT,
            presets_dir,
            "Configuration files (*.ini)",
        )[0]
        if file:
            settings = QSettings(file, QSettings.Format.IniFormat)
            self.set_fields_from_settings(settings)

    def reload_users(self) -> None:
        self.ui.username.clear()
        for username in YouTubeLogin.get_all_usernames():
            self.ui.username.addItem(username, username)
            self.ui.username.setCurrentText(username)

    def save_settings(self) -> None:
        settings = get_settings()
        self.save_settings_from_fields(settings)
        self.settings_changed.emit()

    def load_settings(self) -> None:
        self.reload_users()
        settings = get_settings()
        self.set_fields_from_settings(settings)

    def set_fields_from_settings(self, settings: QSettings) -> None:
        for field in get_all_fields(self.ui):
            field.set(get_setting(field.name, settings))

    def save_settings_from_fields(self, settings: QSettings) -> None:
        for field in get_all_fields(self.ui):
            settings.setValue(field.name, field.get())

    def change_cover_art(self) -> None:
        file = QFileDialog.getOpenFileName(self, "Import album artwork", "", SUPPORTED_IMAGE_FILTER)[0]
        self.ui.coverArt.set(file)

    def show(self) -> None:
        self.ui.show()

    @staticmethod
    def init_combo_boxes(window: QWidget) -> None:
        for child in get_all_children(window):
            if not isinstance(child, QComboBox):
                continue

            for value in SETTINGS_VALUES.COMBO_BOX_VALUES.get(child.objectName(), ()):
                child.addItem(value, value)

    def connect_actions(self) -> None:
        self.ui.buttonBox.accepted.connect(self.save_settings)
        self.ui.buttonBox.rejected.connect(self.reject)
        save_preset = find_child_text(self.ui.buttonBox, SettingsWindow.SAVE_PRESET_TEXT)
        if save_preset and isinstance(save_preset, QPushButton):
            save_preset.clicked.connect(self.save_preset)
        load_preset = find_child_text(self.ui.buttonBox, SettingsWindow.LOAD_PRESET_TEXT)
        if load_preset and isinstance(load_preset, QPushButton):
            load_preset.clicked.connect(self.load_preset)
        self.ui.coverArtButton.clicked.connect(self.change_cover_art)
        self.ui.addNewUserButton.clicked.connect(self.add_new_user)
        self.ui.removeUserButton.clicked.connect(self.remove_user)
