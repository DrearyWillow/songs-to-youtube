from collections.abc import Callable, Iterator
from enum import StrEnum
from typing import ClassVar

from PySide6.QtCore import QObject
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget

from songs_to_youtube.log import applogger
from songs_to_youtube.utils import get_all_children, resource_path

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


def str_to_checkstate(s: str) -> Qt.CheckState:
    str_to_checkstate = {
        SETTINGS_VALUES.CheckBox.UNCHECKED: Qt.CheckState.Unchecked,
        SETTINGS_VALUES.CheckBox.PARTIALLY_CHECKED: Qt.CheckState.PartiallyChecked,
        SETTINGS_VALUES.CheckBox.CHECKED: Qt.CheckState.Checked,
        SETTINGS_VALUES.MULTIPLE_VALUES: Qt.CheckState.PartiallyChecked,
    }
    if s not in str_to_checkstate:
        msg = f"String {s} is not a valid CheckState"
        raise ValueError(msg)
    return str_to_checkstate[s]


def checkstate_to_str(state: Qt.CheckState) -> str:
    c = [
        SETTINGS_VALUES.CheckBox.UNCHECKED,
        SETTINGS_VALUES.MULTIPLE_VALUES,
        SETTINGS_VALUES.CheckBox.CHECKED,
    ]
    return c[state.value]


def int_to_checkstate_str(state: int) -> str:
    c = [
        SETTINGS_VALUES.CheckBox.UNCHECKED,
        SETTINGS_VALUES.MULTIPLE_VALUES,
        SETTINGS_VALUES.CheckBox.CHECKED,
    ]
    return c[state]


def checkstate_to_int(state: Qt.CheckState) -> int:
    c = [
        Qt.CheckState.Unchecked,
        Qt.CheckState.PartiallyChecked,
        Qt.CheckState.Checked,
    ]
    return c.index(state)


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

    # methods for various QWidgets
    # all getters return values as strings
    # all setters take in values as strings
    # all on_update callbacks take in values as strings
    WIDGET_FUNCTIONS: ClassVar[dict[str, dict[str, Callable]]] = {
        "QPlainTextEdit": {
            "getter": lambda widget: widget.toPlainText(),
            "setter": lambda widget, text: widget.setPlainText(text),
            "on_update": lambda widget, cb: widget.textChanged.connect(lambda: cb(widget.toPlainText())),
        },
        "QComboBox": {
            "getter": lambda widget: widget.currentData(),
            "setter": lambda widget, data: widget.setCurrentIndex(widget.findData(data)),
            "on_update": lambda widget, cb: widget.currentIndexChanged.connect(lambda: cb(widget.currentData())),
        },
        "FileComboBox": {
            "getter": lambda widget: widget.currentData(),
            "setter": lambda widget, data: widget.setCurrentIndex(widget.findData(data)),
            "on_update": lambda widget, cb: widget.currentIndexChanged.connect(lambda: cb(widget.currentData())),
        },
        "SettingCheckBox": {
            "getter": lambda widget: checkstate_to_str(widget.checkState()),
            "setter": lambda widget, text: widget.setCheckState(str_to_checkstate(text)),
            "on_update": lambda widget, cb: widget.stateChanged.connect(lambda state: cb(int_to_checkstate_str(state))),
        },
        "CoverArtDisplay": {
            "getter": lambda widget: widget.get(),
            "setter": lambda widget, text: widget.set(text),
            "on_update": lambda widget, cb: widget.imageChanged.connect(cb),
        },
        "QSpinBox": {
            "getter": lambda widget: f"{widget.prefix()}{widget.value()}{widget.suffix()}",
            "setter": lambda widget, text: widget.setValue(
                int(text[len(widget.prefix()) : len(text) - len(widget.suffix())])
            ),
            "on_update": lambda widget, cb: widget.textChanged.connect(cb),
        },
        "QLineEdit": {
            "getter": lambda widget: widget.text(),
            "setter": lambda widget, text: widget.setText(text),
            "on_update": lambda widget, cb: widget.textChanged.connect(cb),
        },
    }

    def __init__(self, widget) -> None:
        self.widget = widget
        self.class_name = widget.metaObject().className()
        self.name = widget.objectName()

    def get(self) -> str:
        return self.WIDGET_FUNCTIONS[self.class_name]["getter"](self.widget)

    def set(self, value) -> None:
        self.WIDGET_FUNCTIONS[self.class_name]["setter"](self.widget, value)

    def on_update(self, function) -> None:
        self.WIDGET_FUNCTIONS[self.class_name]["on_update"](self.widget, function)

    def is_song_field(self) -> bool:
        return self.name in self.SONG_FIELDS

    def is_album_field(self) -> bool:
        return self.name in self.ALBUM_FIELDS


def get_field(obj: QObject, field: str) -> InputField | None:
    for widget in get_all_children(obj):
        class_name = widget.metaObject().className()
        obj_name = widget.objectName()
        if field == obj_name and class_name in InputField.WIDGET_FUNCTIONS:
            return InputField(widget)
    applogger.warning("Could not find field %s", (field,))
    return None


def get_all_fields(obj: QObject) -> Iterator[InputField]:
    """Returns all the input widget children of the given object as InputFields"""
    for widget in get_all_children(obj):
        class_name = widget.metaObject().className()
        if (
            class_name in InputField.WIDGET_FUNCTIONS
            and widget.objectName() != "qt_spinbox_lineedit"
            and "NOFIELD" not in widget.objectName()
        ):
            yield InputField(widget)


def get_all_visible_fields(obj: QObject) -> Iterator[InputField]:
    """Returns all visible InputFields"""
    for widget in get_all_children(obj):
        if isinstance(widget, QWidget) and widget.isVisible():
            class_name = widget.metaObject().className()
            if (
                class_name in InputField.WIDGET_FUNCTIONS
                and widget.objectName() != "qt_spinbox_lineedit"
                and "NOFIELD" not in widget.objectName()
            ):
                yield InputField(widget)
