from collections.abc import Callable, Iterator
from typing import ClassVar, Protocol, TypeVar

from PySide6.QtCore import QObject
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit, QPlainTextEdit, QSpinBox, QWidget

from songs_to_youtube.applogger import applogger
from songs_to_youtube.settings import SETTINGS_VALUES, CoverArtDisplay, FileComboBox, SettingCheckBox
from songs_to_youtube.utils import get_all_children


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


class FieldAdapter(Protocol):
    def get(self) -> str: ...
    def set(self, value: str) -> None: ...
    def on_update(self, callback: Callable[[str], None]) -> None: ...


W = TypeVar("W", bound=QWidget)


def narrow_qwidget[W: QWidget](widget: QWidget, widget_type: type[W]) -> W:
    if not isinstance(widget, widget_type):
        msg = f"Expected {widget_type.__name__}, got {type(widget).__name__}"
        raise TypeError(msg)
    return widget


class QPlainTextEditAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, QPlainTextEdit)

    def get(self) -> str:
        return self.widget.toPlainText()

    def set(self, value: str) -> None:
        self.widget.setPlainText(value)

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.widget.textChanged.connect(lambda: callback(self.get()))


class QComboBoxAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, QComboBox)

    def get(self) -> str:
        return self.widget.currentData()

    def set(self, value: str) -> None:
        self.widget.setCurrentIndex(self.widget.findData(value))

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.widget.currentIndexChanged.connect(lambda: callback(self.get()))


class FileComboBoxAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, FileComboBox)

    def get(self) -> str:
        return self.widget.currentData()

    def set(self, value: str) -> None:
        self.widget.setCurrentIndex(self.widget.findData(value))

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.widget.currentIndexChanged.connect(lambda: callback(self.get()))


class SettingCheckBoxAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, SettingCheckBox)

    def get(self) -> str:
        return checkstate_to_str(self.widget.checkState())

    def set(self, value: str) -> None:
        self.widget.setCheckState(str_to_checkstate(value))

    def on_update(self, callback: Callable[[str], None]) -> None:
        def state_changed_connect(state: int) -> None:
            return callback(int_to_checkstate_str(state))

        self.widget.stateChanged.connect(state_changed_connect)


class CoverArtDisplayAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, CoverArtDisplay)

    def get(self) -> str:
        return self.widget.get()

    def set(self, value: str) -> None:
        self.widget.set(value)

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.widget.imageChanged.connect(callback)


class QSpinBoxAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, QSpinBox)

    def get(self) -> str:
        return f"{self.widget.prefix()}{self.widget.value()}{self.widget.suffix()}"

    def set(self, value: str) -> None:
        prefix = self.widget.prefix()
        suffix = self.widget.suffix()
        number = value[len(prefix) : len(value) - len(suffix)]
        self.widget.setValue(int(number))

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.widget.textChanged.connect(callback)


class QLineEditAdapter:
    def __init__(self, widget: QWidget) -> None:
        self.widget = narrow_qwidget(widget, QLineEdit)

    def get(self) -> str:
        return self.widget.text()

    def set(self, value: str) -> None:
        self.widget.setText(value)

    def on_update(self, callback: Callable[[str], None]) -> None:
        self.widget.textChanged.connect(callback)


class AdapterFactory(Protocol):
    def __call__(self, widget: QWidget) -> FieldAdapter: ...


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


def get_field(obj: QObject, field: str) -> InputField | None:
    for widget in get_all_children(obj):
        if not isinstance(widget, QWidget):
            continue

        class_name = widget.metaObject().className()
        obj_name = widget.objectName()

        if field == obj_name and class_name in InputField.ADAPTERS:
            return InputField(widget)

    applogger.warning("Could not find field %s", field)
    return None


def get_all_fields(obj: QObject) -> Iterator[InputField]:
    """Returns all the input widget children of the given object as InputFields."""
    for widget in get_all_children(obj):
        if not isinstance(widget, QWidget):
            continue

        class_name = widget.metaObject().className()

        if (
            class_name in InputField.ADAPTERS
            and widget.objectName() != "qt_spinbox_lineedit"
            and "NOFIELD" not in widget.objectName()
        ):
            yield InputField(widget)


def get_all_visible_fields(obj: QObject) -> Iterator[InputField]:
    """Returns all visible InputFields."""
    for widget in get_all_children(obj):
        if not isinstance(widget, QWidget) or not widget.isVisible():
            continue

        class_name = widget.metaObject().className()

        if (
            class_name in InputField.ADAPTERS
            and widget.objectName() != "qt_spinbox_lineedit"
            and "NOFIELD" not in widget.objectName()
        ):
            yield InputField(widget)
