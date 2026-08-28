from enum import IntEnum, StrEnum
from typing import ClassVar

from PySide6.QtCore import Qt

from songs_to_youtube.utils import resource_path


class TreeWidgetType(IntEnum):
    SONG = 0
    ALBUM = 1


class CustomDataRole(IntEnum):
    ITEMTYPE = Qt.ItemDataRole.UserRole
    ITEMDATA = Qt.ItemDataRole.UserRole + 1


ORGANIZATION = "7x11x13"
APPLICATION = "songs-to-youtube"
VERSION = "v0.13.2"
SETTINGS_FILENAME = "v0.8settings"

SUPPORTED_IMAGE_FILTER = "Images (*.bmp *.cur *.gif *.icns *.ico *.jpeg *.jpg *.pbm *.pgm *.png *.ppm *.svg *.svgz *.tga *.tif *.tiff *.wbmp *.webp *.xbm *.xpm)"


APPLICATION_IMAGES: dict[str, str] = {
    ":/image/default.jpg": resource_path("image/default.jpg"),
    ":/image/multiple-values.png": resource_path("image/multiple-values.png"),
    ":/image/icon.ico": resource_path("image/icon.ico"),
}


class SETTINGS_VALUES:
    MULTIPLE_VALUES = "<<Multiple values>>"
    MULTIPLE_VALUES_IMG = APPLICATION_IMAGES[":/image/multiple-values.png"]

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
