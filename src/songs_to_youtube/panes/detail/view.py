from PySide6.QtCore import Signal
from PySide6.QtGui import QKeyEvent, QResizeEvent, Qt
from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QGroupBox, QLabel, QPushButton, QWidget

from songs_to_youtube.const import TreeWidgetType
from songs_to_youtube.field import get_all_fields
from songs_to_youtube.settings import CoverArtDisplay, FileComboBox, SettingCheckBox, SettingsScrollArea
from songs_to_youtube.utils import init_combo_boxes, load_ui


class DetailView(QWidget):
    saveSettings = Signal()
    loadSettings = Signal()
    coverArtChanged = Signal()
    albumFieldChanged = Signal(str)
    ytCheckboxChanged = Signal(str)
    fieldUpdated = Signal(str, str)

    SONG_ONLY_WIDGETS = (
        (QGroupBox, "ffmpegSettings"),
        (QGroupBox, "youtubeSettings"),
    )
    ALBUM_ONLY_WIDGETS = (
        (QComboBox, "albumPlaylist"),
        (QLabel, "albumPlaylistLabel"),
        (QGroupBox, "ffmpegSettingsAlbum"),
        (QGroupBox, "youtubeSettingsAlbum"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        self.item_type = TreeWidgetType.ALBUM
        super().__init__(parent)
        load_ui("songsettingswindow.ui", (SettingCheckBox, CoverArtDisplay, SettingsScrollArea, FileComboBox), self)
        init_combo_boxes(self)
        self.setVisible(False)
        self.connect_actions()

    def resizeEvent(self, event: QResizeEvent) -> None:
        # resize UI when widget is resized
        if child := self.findChild(QWidget, "songSettingsWindow"):
            child.resize(event.size())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_S:
            self.saveSettings.emit()
        super().keyPressEvent(event)

    def connect_actions(self) -> None:
        if cover_art_button := self.findChild(QPushButton, "coverArtButton"):
            cover_art_button.clicked.connect(self.coverArtChanged.emit)
        if button_box := self.findChild(QDialogButtonBox):
            button_box.accepted.connect(self.saveSettings.emit)
            button_box.rejected.connect(self.loadSettings.emit)

        for field in get_all_fields(self):
            field.on_update(lambda text, field_name=field.name: self.fieldUpdated.emit(field_name, text))
            if field.name == "albumPlaylist":
                field.on_update(self.albumFieldChanged.emit)
            elif field.name == "uploadYouTube":
                field.on_update(self.ytCheckboxChanged.emit)

    def set_button_box_enabled(self, *, enabled: bool) -> None:
        if child := self.findChild(QDialogButtonBox):
            child.setEnabled(enabled)

    def set_child_enabled(self, name: str, *, enabled: bool) -> None:
        if child := self.findChild(QGroupBox, name):
            child.setEnabled(enabled)

    def set_upload_youtube_enabled(self, *, enabled: bool) -> None:
        if upload_yt_checkbox := self.findChild(SettingCheckBox, "uploadYouTube"):
            upload_yt_checkbox.setEnabled(enabled)

    def set_widget_visibility(self, *, is_album: bool) -> None:
        for widget in self.SONG_ONLY_WIDGETS:
            if child_widget := self.findChild(*widget):
                child_widget.setVisible(not is_album)
        for widget in self.ALBUM_ONLY_WIDGETS:
            if child_widget := self.findChild(*widget):
                child_widget.setVisible(is_album)

    def set_visible(self, *, visible: bool) -> None:
        self.setVisible(visible)

    def is_child_enabled(self, name: str) -> bool:
        child_enabled = False
        if child := self.findChild(QGroupBox, name):
            child_enabled = child.isEnabled()
        return child_enabled
