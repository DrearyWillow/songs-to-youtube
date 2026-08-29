
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget

from songs_to_youtube.applogger import applogger
from songs_to_youtube.fields.input_field import InputField
from songs_to_youtube.utils import get_all_children

if TYPE_CHECKING:
    from collections.abc import Iterator

    from PySide6.QtCore import QObject


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
