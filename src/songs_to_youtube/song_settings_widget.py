from PySide6.QtCore import QItemSelection, QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QKeyEvent, QResizeEvent, Qt
from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFileDialog, QGroupBox, QLabel, QPushButton, QWidget

from songs_to_youtube.const import SUPPORTED_IMAGE_FILTER, CustomDataRole, TreeWidgetType
from songs_to_youtube.field import SETTINGS_VALUES, get_all_fields, get_all_visible_fields, get_field
from songs_to_youtube.log import applogger
from songs_to_youtube.settings import CoverArtDisplay, FileComboBox, SettingCheckBox, SettingsScrollArea, SettingsWindow
from songs_to_youtube.utils import load_ui


class SongSettingsWidget(QWidget):
    SONG_ONLY_WIDGETS = ((QGroupBox, "ffmpegSettings"), (QGroupBox, "youtubeSettings"))
    ALBUM_ONLY_WIDGETS = (
        (QComboBox, "albumPlaylist"),
        (QLabel, "albumPlaylistLabel"),
        (QGroupBox, "ffmpegSettingsAlbum"),
        (QGroupBox, "youtubeSettingsAlbum"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        # which items are currently selected by the song tree widget
        self.tree_indexes: set[QModelIndex | QPersistentModelIndex] = set()

        # which fields have been updated since we loaded data
        # this gets reset when we save the field data
        # and every time we load new data
        self.fields_updated: set[str] = set()

        # values of each field when the window is loaded
        self.field_original_values = {}

        self.item_type = TreeWidgetType.ALBUM

        super().__init__(parent)
        load_ui("songsettingswindow.ui", (SettingCheckBox, CoverArtDisplay, SettingsScrollArea, FileComboBox), self)
        SettingsWindow.init_combo_boxes(self)
        self.setVisible(False)
        self.connect_actions()

    def resizeEvent(self, event: QResizeEvent) -> None:
        # resize UI when widget is resized
        if child := self.findChild(QWidget, "songSettingsWindow"):
            child.resize(event.size())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_S:
            self.save_settings()
        super().keyPressEvent(event)

    def connect_actions(self) -> None:
        if cover_art_button := self.findChild(QPushButton, "coverArtButton"):
            cover_art_button.clicked.connect(self.change_cover_art)
        if button_box := self.findChild(QDialogButtonBox):
            button_box.accepted.connect(self.save_settings)
            button_box.rejected.connect(self.load_settings)
        for field in get_all_fields(self):
            field.on_update(lambda text, field_name=field.name: self.on_field_updated(field_name, text))
            if field.name == "albumPlaylist":
                # disable album settings whenever album mode is set to multiple values
                field.on_update(
                    lambda data: self.set_album_enabled(enabled=(data != SETTINGS_VALUES.AlbumPlaylist.MULTIPLE))
                )
            elif field.name == "uploadYouTube":
                # disable youtube settings whenever 'upload to youtube' is unchecked
                field.on_update(
                    lambda text: self.set_youtube_enabled(enabled=(text != SETTINGS_VALUES.CheckBox.UNCHECKED))
                )

    def change_cover_art(self) -> None:
        dir_setting = "song_dir" if self.item_type == TreeWidgetType.SONG else "album_dir"
        file, directory = None, None
        for e in self.tree_indexes:
            directory = e.data(CustomDataRole.ITEMDATA).get_value(dir_setting)
            break
        if directory:
            file = QFileDialog.getOpenFileName(self, "Import album artwork", directory, SUPPORTED_IMAGE_FILTER)[0]
        if file and (cover_art_display := self.findChild(CoverArtDisplay)):
            cover_art_display.set(file)

    def set_youtube_enabled(self, *, enabled: bool) -> None:
        if self.item_type == TreeWidgetType.SONG:
            if youtube_song_settings := self.findChild(QGroupBox, "youtubeSettings"):
                youtube_song_settings.setEnabled(enabled)
        else:
            # if album settings are disabled, we can't enable youtube settings
            ffmpeg_album_enabled = False
            if ffmpeg_album_settings := self.findChild(QGroupBox, "ffmpegSettingsAlbum"):
                ffmpeg_album_enabled = ffmpeg_album_settings.isEnabled()
            enabled = enabled and ffmpeg_album_enabled
            if youtube_album_settings := self.findChild(QGroupBox, "youtubeSettingsAlbum"):
                youtube_album_settings.setEnabled(enabled)

    def set_button_box_enabled(self, *, enabled: bool) -> None:
        if child := self.findChild(QDialogButtonBox):
            child.setEnabled(enabled)

    def set_album_enabled(self, *, enabled: bool) -> None:
        if ffmpeg_album := self.findChild(QGroupBox, "ffmpegSettingsAlbum"):
            ffmpeg_album.setEnabled(enabled)
        if upload_yt := self.findChild(SettingCheckBox, "uploadYouTube"):
            upload_yt.setEnabled(enabled)
        # if youtube settings are disabled, we can't enable them
        upload_yt_enabled = False
        if upload_youtube_field := get_field(self, "uploadYouTube"):
            upload_yt_enabled = upload_youtube_field.get() != SETTINGS_VALUES.CheckBox.UNCHECKED
        enabled = enabled and upload_yt_enabled
        if yt_settings_album := self.findChild(QGroupBox, "youtubeSettingsAlbum"):
            yt_settings_album.setEnabled(enabled)

    def on_field_updated(self, field: str, current_value: str) -> None:
        if field not in self.field_original_values:
            # just loaded field, set original value to loaded value
            self.field_original_values[field] = current_value
            return

        original_value = self.field_original_values[field]
        if original_value == current_value:
            self.fields_updated.discard(field)
        else:
            self.fields_updated.add(field)

        self.set_button_box_enabled(enabled=(len(self.fields_updated) == 0))

    def save_settings(self) -> None:
        self.fields_updated = set()
        self.field_original_values: dict[str, str] = {}
        self.set_button_box_enabled(enabled=False)
        for data in {i.data(CustomDataRole.ITEMDATA) for i in self.tree_indexes}:
            for field in get_all_visible_fields(self):
                value = field.get()
                if value != SETTINGS_VALUES.MULTIPLE_VALUES:
                    try:
                        data.set_value(field.name, value)
                    except Exception:
                        applogger.error(f"Error while setting {field.name} with value {value}")
                self.field_original_values[field.name] = value
        self.load_settings()

    def load_settings(self) -> None:
        # update UI to show/hide appropriate elements
        # based on the type of items we are editing
        for widget in self.SONG_ONLY_WIDGETS:
            if child_widget := self.findChild(*widget):
                child_widget.setVisible(self.item_type == TreeWidgetType.SONG)
        for widget in self.ALBUM_ONLY_WIDGETS:
            if child_widget := self.findChild(*widget):
                child_widget.setVisible(self.item_type == TreeWidgetType.ALBUM)

        if self.item_type == TreeWidgetType.SONG and (
            upload_yt_checkbox := self.findChild(SettingCheckBox, "uploadYouTube")
        ):
            upload_yt_checkbox.setEnabled(True)

        self.fields_updated = set()
        self.field_original_values = {}
        self.set_button_box_enabled(enabled=False)
        items = [i.data(CustomDataRole.ITEMDATA).to_dict() for i in self.tree_indexes]
        # set settings based on selected items
        for field in get_all_visible_fields(self):
            values = {dict(i)[field.name] for i in items if field.name in i}
            if len(values) == 0:
                continue
            has_multiple_values = len(values) > 1
            value = values.pop() if not has_multiple_values else SETTINGS_VALUES.MULTIPLE_VALUES
            if field.name == "albumPlaylist":
                # show album settings when at least one single video album is selected
                self.set_album_enabled(enabled=(value != SETTINGS_VALUES.AlbumPlaylist.MULTIPLE))
            elif field.name == "uploadYouTube":
                # show youtube settings when at least one song is to be uploaded is unchecked
                self.set_youtube_enabled(enabled=(value != SETTINGS_VALUES.CheckBox.UNCHECKED))
            if isinstance(field.widget, QComboBox):
                if isinstance(field.widget, FileComboBox):
                    field.widget.reload()
                # add <<Multiple values>> to combobox as necessary
                multiple_values_index = field.widget.findData(SETTINGS_VALUES.MULTIPLE_VALUES)
                if not has_multiple_values and multiple_values_index != -1:
                    field.set(value)
                    field.widget.removeItem(multiple_values_index)
                elif has_multiple_values and multiple_values_index == -1:
                    field.widget.addItem(SETTINGS_VALUES.MULTIPLE_VALUES, SETTINGS_VALUES.MULTIPLE_VALUES)
                    field.set(value)
                else:
                    field.set(value)
            else:
                field.set(value)
            self.field_original_values[field.name] = value

    def song_tree_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        selected_indexes = {QPersistentModelIndex(i) for i in selected.indexes()}
        deselected_indexes = {QPersistentModelIndex(i) for i in deselected.indexes()}
        self.tree_indexes |= selected_indexes  # add new selected indexes
        self.tree_indexes -= deselected_indexes  # remove deselected indexes
        self.setVisible(bool(self.tree_indexes))  # hide window if nothing is selected
        if self.tree_indexes:
            index = next(iter(self.tree_indexes))
            # all indexes will have the same item type
            # guaranteed by our selection model
            self.item_type = index.data(CustomDataRole.ITEMTYPE)
            self.load_settings()
