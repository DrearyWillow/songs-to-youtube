from PySide6.QtCore import QItemSelection, QModelIndex, QPersistentModelIndex
from PySide6.QtWidgets import QComboBox, QFileDialog, QWidget

from songs_to_youtube.applogger import applogger
from songs_to_youtube.components.detail.view import DetailView
from songs_to_youtube.const import SETTINGS_VALUES, SUPPORTED_IMAGE_FILTER, CustomDataRole, TreeWidgetType
from songs_to_youtube.custom_widgets import CoverArtDisplay, FileComboBox
from songs_to_youtube.field import get_all_visible_fields, get_field


class DetailPresenter:
    def __init__(self, parent: QWidget) -> None:
        # which items are currently selected by the song tree widget
        self.tree_indexes: set[QModelIndex | QPersistentModelIndex] = set()

        # which fields have been updated since we loaded data
        # this gets reset when we save the field data
        # and every time we load new data
        self.fields_updated: set[str] = set()

        # values of each field when the window is loaded
        self.field_original_values = {}

        self.view = DetailView(parent)
        self.view.saveSettings.connect(self.save_settings)
        self.view.loadSettings.connect(self.load_settings)
        self.view.coverArtChanged.connect(self.change_cover_art)
        self.view.albumFieldChanged.connect(self.on_album_mode_change)
        self.view.ytCheckboxChanged.connect(self.on_youtube_checkbox_change)
        self.view.fieldUpdated.connect(self.on_field_updated)

        self.item_type = TreeWidgetType.ALBUM

    def change_cover_art(self) -> None:
        dir_setting = "song_dir" if self.item_type == TreeWidgetType.SONG else "album_dir"
        file, directory = None, None
        directory = next((e.data(CustomDataRole.ITEMDATA).get_value(dir_setting) for e in self.tree_indexes), None)
        if directory:
            file = QFileDialog.getOpenFileName(self.view, "Import album artwork", directory, SUPPORTED_IMAGE_FILTER)[0]
        if file and (cover_art_display := self.view.findChild(CoverArtDisplay)):
            cover_art_display.set(file)

    def set_youtube_enabled(self, *, enabled: bool) -> None:
        if self.item_type == TreeWidgetType.SONG:
            self.view.set_child_enabled("youtubeSettings", enabled=enabled)
        else:
            # if album settings are disabled, we can't enable youtube settings
            enabled = enabled and self.view.is_child_enabled("ffmpegSettingsAlbum")
            self.view.set_child_enabled("youtubeSettingsAlbum", enabled=enabled)

    def set_album_enabled(self, *, enabled: bool) -> None:
        self.view.set_child_enabled("ffmpegSettingsAlbum", enabled=enabled)
        self.view.set_upload_youtube_enabled(enabled=enabled)
        # if youtube settings are disabled, we can't enable them
        upload_yt_enabled = False
        if upload_youtube_field := get_field(self.view, "uploadYouTube"):
            upload_yt_enabled = upload_youtube_field.get() != SETTINGS_VALUES.CheckBox.UNCHECKED
        enabled = enabled and upload_yt_enabled
        self.view.set_child_enabled("youtubeSettingsAlbum", enabled=enabled)

    def on_album_mode_change(self, data: str) -> None:
        # disable album settings whenever album mode is set to multiple values
        self.set_album_enabled(enabled=(data != SETTINGS_VALUES.AlbumPlaylist.MULTIPLE))

    def on_youtube_checkbox_change(self, text: str) -> None:
        # disable youtube settings whenever 'upload to youtube' is unchecked
        self.set_youtube_enabled(enabled=(text != SETTINGS_VALUES.CheckBox.UNCHECKED))

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

        self.view.set_button_box_enabled(enabled=(len(self.fields_updated) == 0))

    def save_settings(self) -> None:
        self.fields_updated = set()
        self.field_original_values: dict[str, str] = {}
        self.view.set_button_box_enabled(enabled=False)
        for data in {i.data(CustomDataRole.ITEMDATA) for i in self.tree_indexes}:
            for field in get_all_visible_fields(self.view):
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
        self.view.set_widget_visibility(is_album=(self.item_type == TreeWidgetType.ALBUM))

        if self.item_type == TreeWidgetType.SONG:
            self.view.set_upload_youtube_enabled(enabled=True)

        self.fields_updated = set()
        self.field_original_values = {}
        self.view.set_button_box_enabled(enabled=False)
        items = [i.data(CustomDataRole.ITEMDATA).to_dict() for i in self.tree_indexes]
        # set settings based on selected items
        for field in get_all_visible_fields(self.view):
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

        # hide window if nothing is selected
        self.view.set_visible(visible=bool(self.tree_indexes))

        if self.tree_indexes:
            index = next(iter(self.tree_indexes))
            # all indexes will have the same item type
            # guaranteed by our selection model
            self.item_type = index.data(CustomDataRole.ITEMTYPE)
            self.load_settings()
