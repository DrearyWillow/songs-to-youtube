import pathlib

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QFileDialog, QWidget

from songs_to_youtube.dialogs.add_user.add_user import AddUserWindow
from songs_to_youtube.dialogs.settings.view import SettingsWindowView
from songs_to_youtube.utils import get_all_usernames, get_setting, get_settings, remove_user_cookies, resource_path


class SettingsWindowPresenter(QWidget):
    settingsChanged = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__()
        self.view = SettingsWindowView(parent)
        self.load_settings()

        self.view.saveSettings.connect(self.save_settings)
        self.view.savePreset.connect(self.save_preset)
        self.view.loadPreset.connect(self.load_preset)
        self.view.addNewUser.connect(self.add_new_user)
        self.view.removeUser.connect(self.remove_user)

    def add_new_user(self) -> None:
        self.msg_box = AddUserWindow()
        self.msg_box.accepted.connect(self.reload_users)
        self.msg_box.show()

    def reload_users(self) -> None:
        self.view.clear_username()
        for username in get_all_usernames():
            self.view.add_username(username)

    def remove_user(self) -> None:
        if self.view.get_current_username():
            remove_user_cookies(self.view.get_current_username())
            self.view.remove_current_username()

    def save_preset(self) -> None:
        presets_dir = resource_path("config")
        if not pathlib.Path(presets_dir).exists():
            pathlib.Path(presets_dir).mkdir(parents=True)
        file = QFileDialog.getSaveFileName(
            self.view,
            self.view.SAVE_PRESET_TEXT,
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
            self.view,
            self.view.LOAD_PRESET_TEXT,
            presets_dir,
            "Configuration files (*.ini)",
        )[0]
        if file:
            settings = QSettings(file, QSettings.Format.IniFormat)
            self.set_fields_from_settings(settings)

    def save_settings(self) -> None:
        settings = get_settings()
        self.save_settings_from_fields(settings)
        self.settingsChanged.emit()

    def load_settings(self) -> None:
        self.reload_users()
        settings = get_settings()
        self.set_fields_from_settings(settings)

    def set_fields_from_settings(self, settings: QSettings) -> None:
        for field in self.view.get_all_fields():
            field.set(get_setting(field.name, settings))

    def save_settings_from_fields(self, settings: QSettings) -> None:
        for field in self.view.get_all_fields():
            settings.setValue(field.name, field.get())
