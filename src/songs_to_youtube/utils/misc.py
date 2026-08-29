from enum import StrEnum
from typing import ClassVar

from songs_to_youtube.utils import resource_path

APPLICATION_IMAGES: dict[str, str] = {
    ":/assets/default.jpg": resource_path("assets/default.jpg"),
    ":/assets/multiple-values.png": resource_path("assets/multiple-values.png"),
    ":/assets/icon.ico": resource_path("assets/icon.ico"),
}


class SETTINGS_VALUES:
    MULTIPLE_VALUES = "<<Multiple values>>"
    MULTIPLE_VALUES_IMG = APPLICATION_IMAGES[":/assets/multiple-values.png"]

    # combo box values

    class DragAndDrop(StrEnum):
        ALBUM_MODE = "Album mode"
        SONG_MODE = "Song mode"

    class LogLevel(StrEnum):
        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"

    class AlbumPlaylist(StrEnum):
        MULTIPLE = "Multiple videos"
        SINGLE = "Single video"

    class VideoVisibility(StrEnum):
        PUBLIC = "PUBLIC"
        UNLISTED = "UNLISTED"

    COMBO_BOX_VALUES: ClassVar[dict[str, set[str]]] = {
        "dragAndDropBehavior": {item.value for item in DragAndDrop},
        "logLevel": {item.value for item in LogLevel},
        "albumPlaylist": {item.value for item in AlbumPlaylist},
        "videoVisibility": {item.value for item in VideoVisibility},
        "videoVisibilityAlbum": {item.value for item in VideoVisibility},
    }

    class CheckBox(StrEnum):
        UNCHECKED = "PySide6.QtCore.Qt.CheckState.Unchecked"
        PARTIALLY_CHECKED = "PySide6.QtCore.Qt.CheckState.PartiallyChecked"
        CHECKED = "PySide6.QtCore.Qt.CheckState.Checked"
