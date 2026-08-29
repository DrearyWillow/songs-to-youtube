from typing import TYPE_CHECKING, Protocol, TypeVar

from PySide6.QtWidgets import QComboBox, QLineEdit, QPlainTextEdit, QSpinBox, QWidget

from songs_to_youtube.custom_widgets.check_box import SettingCheckBox
from songs_to_youtube.custom_widgets.cover_art_display import CoverArtDisplay
from songs_to_youtube.custom_widgets.file_combo_box import FileComboBox
from songs_to_youtube.fields.utils import checkstate_to_str, int_to_checkstate_str, str_to_checkstate

if TYPE_CHECKING:
    from collections.abc import Callable


class FieldAdapter(Protocol):
    def get(self) -> str: ...
    def set(self, value: str) -> None: ...
    def on_update(self, callback: Callable[[str], None]) -> None: ...


class AdapterFactory(Protocol):
    def __call__(self, widget: QWidget) -> FieldAdapter: ...


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
