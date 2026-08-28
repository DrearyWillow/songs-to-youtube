import posixpath
import sys
from collections.abc import Iterable, Iterator

from PySide6.QtCore import (
    QFile,
    QIODeviceBase,
    QMimeData,
    QObject,
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QComboBox, QWidget

from songs_to_youtube.applogger import applogger
from songs_to_youtube.const import SETTINGS_VALUES
from songs_to_youtube.utils.files import file_is_image, resource_path


def get_all_children(obj: QObject) -> Iterator[QObject]:
    """Returns all the children (recursive) of the given object"""
    for child in obj.children():
        yield child
        yield from get_all_children(child)


def find_child_text(obj: QObject, text: str) -> QObject | None:
    """Returns the child of obj with the given text"""
    for child in obj.children():
        get_text = getattr(child, "text", None)
        if callable(get_text) and get_text() == text:
            return child
    return None


# TODO (drearywillow): make this a Type Generic narrowing function
def find_ancestor(obj: QObject, obj_type: str = "", name: str = "") -> QObject | None:
    """Returns the closest ancestor of obj with type and name given"""
    ancestor = obj.parent()
    if not ancestor:
        return None
    # used recursion here before but pyside
    # deleted the object before returning
    while ancestor and not (
        (not name or ancestor.objectName() == name)
        and (not obj_type or ancestor.metaObject().className() == str(obj_type))
    ):
        ancestor = ancestor.parent()
    return ancestor


def load_ui(name: str, custom_widgets: Iterable[object] | None = None, parent: QWidget | None = None) -> QWidget:
    custom_widgets = custom_widgets or []
    loader = QUiLoader()
    for cw in custom_widgets:
        loader.registerCustomWidget(cw)
    path = resource_path(posixpath.join("ui", name))
    ui_file = QFile(path)
    if not ui_file.open(QIODeviceBase.OpenModeFlag.ReadOnly):
        applogger.error("Cannot open %s: %s", path, ui_file.errorString())
        sys.exit(-1)
    ui = loader.load(ui_file, parent)
    ui_file.close()
    return ui


def mimedata_has_image(data: QMimeData) -> bool:
    """Returns True if the given mimedata contains a valid image file"""
    return any(file_is_image(url.toLocalFile()) for url in data.urls())


def get_image_from_mimedata(data: QMimeData) -> str | None:
    """Returns a valid image path from the given mimedata if possible, otherwise returns None"""
    for url in data.urls():
        if file_is_image(url.toLocalFile()):
            return url.toLocalFile()
    return None


def make_value_qt_safe(value: str | list[str]) -> str:
    if isinstance(value, list):
        if len(value) > 0:
            return str(value[0])
        return ""
    return str(value)


def init_combo_boxes(window: QWidget) -> None:
    for child in get_all_children(window):
        if not isinstance(child, QComboBox):
            continue

        for value in SETTINGS_VALUES.COMBO_BOX_VALUES.get(child.objectName(), ()):
            child.addItem(value, value)
