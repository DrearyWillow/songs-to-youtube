from collections.abc import Iterator
from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QPushButton,
    QWidget,
)

from songs_to_youtube.const import SUPPORTED_IMAGE_FILTER
from songs_to_youtube.custom_widgets import CoverArtDisplay, FileComboBox, SettingCheckBox, SettingsScrollArea
from songs_to_youtube.field import InputField, get_all_fields
from songs_to_youtube.utils import init_combo_boxes, load_ui


class SettingsWindowUI(QDialog):
    buttonBox: QDialogButtonBox
    username: QComboBox
    coverArt: CoverArtDisplay
    coverArtButton: QPushButton
    addNewUserButton: QPushButton
    removeUserButton: QPushButton


class SettingsWindowView(QDialog):
    saveSettings = Signal()
    savePreset = Signal()
    loadPreset = Signal()
    addNewUser = Signal()
    removeUser = Signal()

    SAVE_PRESET_TEXT = "Save preset"
    LOAD_PRESET_TEXT = "Load preset"

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.ui = cast(
            "SettingsWindowUI",
            load_ui(
                "settingswindow.ui",
                (
                    CoverArtDisplay,
                    SettingCheckBox,
                    SettingsScrollArea,
                    FileComboBox,
                ),
            ),
        )
        # rename default buttons
        self.save_preset_btn = self.ui.buttonBox.addButton(self.SAVE_PRESET_TEXT, QDialogButtonBox.ButtonRole.ApplyRole)
        self.load_preset_btn = self.ui.buttonBox.addButton(self.LOAD_PRESET_TEXT, QDialogButtonBox.ButtonRole.ApplyRole)
        init_combo_boxes(self.ui)
        self.connect_actions()

    def get_all_fields(self) -> Iterator[InputField]:
        return get_all_fields(self.ui)

    def get_current_username(self) -> str:
        return self.ui.username.currentText()

    def clear_username(self) -> None:
        self.ui.username.clear()

    def add_username(self, username: str) -> None:
        self.ui.username.addItem(username, username)
        self.ui.username.setCurrentText(username)

    def remove_current_username(self) -> None:
        self.ui.username.removeItem(self.ui.username.currentIndex())

    def change_cover_art(self) -> None:
        file = QFileDialog.getOpenFileName(self, "Import album artwork", "", SUPPORTED_IMAGE_FILTER)[0]
        self.ui.coverArt.set(file)

    def show(self) -> None:
        self.ui.show()

    def connect_actions(self) -> None:
        self.ui.buttonBox.accepted.connect(self.saveSettings.emit)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.save_preset_btn.clicked.connect(self.savePreset.emit)
        self.load_preset_btn.clicked.connect(self.loadPreset.emit)
        self.ui.coverArtButton.clicked.connect(self.change_cover_art)
        self.ui.addNewUserButton.clicked.connect(self.addNewUser.emit)
        self.ui.removeUserButton.clicked.connect(self.removeUser.emit)
