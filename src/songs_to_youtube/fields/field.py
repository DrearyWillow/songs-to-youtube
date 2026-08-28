from collections.abc import Callable
from typing import ClassVar

from PySide6.QtWidgets import QWidget

from songs_to_youtube.fields.adapters import (
    AdapterFactory,
    CoverArtDisplayAdapter,
    FileComboBoxAdapter,
    QComboBoxAdapter,
    QLineEditAdapter,
    QPlainTextEditAdapter,
    QSpinBoxAdapter,
    SettingCheckBoxAdapter,
)


class InputField:
    SONG_FIELDS: ClassVar[set[str]] = {
        "backgroundColor",
        "videoHeight",
        "videoWidth",
        "uploadYouTube",
        "coverArt",
        "videoDescription",
        "videoTags",
        "videoTitle",
        "videoVisibility",
        "fileOutputDir",
        "fileOutputName",
        "playlistName",
        "commandName",
        "notifySubs",
    }

    ALBUM_FIELDS: ClassVar[set[str]] = {
        "albumPlaylist",
        "fileOutputDirAlbum",
        "fileOutputNameAlbum",
        "uploadYouTube",
        "videoDescriptionAlbum",
        "videoTagsAlbum",
        "videoTitleAlbum",
        "videoVisibilityAlbum",
        "notifySubsAlbum",
        "concatCommandName",
    }

    ADAPTERS: ClassVar[dict[str, AdapterFactory]] = {
        "QPlainTextEdit": QPlainTextEditAdapter,
        "QComboBox": QComboBoxAdapter,
        "FileComboBox": FileComboBoxAdapter,
        "SettingCheckBox": SettingCheckBoxAdapter,
        "CoverArtDisplay": CoverArtDisplayAdapter,
        "QSpinBox": QSpinBoxAdapter,
        "QLineEdit": QLineEditAdapter,
    }

    def __init__(self, widget: QWidget) -> None:
        self.widget = widget
        self.class_name = widget.metaObject().className()
        self.name = widget.objectName()
        self.adapter = self.ADAPTERS[self.class_name](widget)

    def get(self) -> str:
        return self.adapter.get()

    def set(self, value: str) -> None:
        self.adapter.set(value)

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.adapter.on_update(callback)

    def is_song_field(self) -> bool:
        return self.name in self.SONG_FIELDS

    def is_album_field(self) -> bool:
        return self.name in self.ALBUM_FIELDS
