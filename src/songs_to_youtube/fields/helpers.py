from collections.abc import Iterator

from PySide6.QtCore import QObject
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget

from songs_to_youtube.applogger import applogger
from songs_to_youtube.const import SETTINGS_VALUES
from songs_to_youtube.fields.field import InputField
from songs_to_youtube.utils import get_all_children


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
