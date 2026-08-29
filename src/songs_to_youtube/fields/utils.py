from PySide6.QtGui import Qt

from songs_to_youtube.utils.misc import SETTINGS_VALUES


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
