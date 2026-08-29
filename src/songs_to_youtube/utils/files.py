from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, QDirIterator, QFileInfo, QMimeDatabase

from songs_to_youtube.applogger import applogger

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def files_in_directory(dir_path: str) -> Iterator[str]:
    """Generates all the files of the given directory"""
    file = QDirIterator(dir_path, QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
    while file.hasNext():
        yield file.next()


def files_in_directory_and_subdirectories(dir_path: str) -> Iterator[str]:
    """Generates all the files in the given directory and subdirectories"""
    file = QDirIterator(
        dir_path,
        QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot,
        QDirIterator.IteratorFlag.Subdirectories | QDirIterator.IteratorFlag.FollowSymlinks,
    )
    while file.hasNext():
        yield file.next()


def file_is_type(file_path: str, mime_prefix: str, exclude: Iterable[str] | None = None) -> bool:
    exclude = exclude or []
    info = QFileInfo(file_path)
    if not info.isReadable():
        applogger.info("File %s is not readable", (info.filePath(),))
        return False
    db = QMimeDatabase()
    mime_type = db.mimeTypeForFile(info)
    return mime_type.name().startswith(mime_prefix) and mime_type.name() not in exclude


def file_is_audio(file_path: str) -> bool:
    """Returns true if the given file is a readable audio file"""
    return file_is_type(file_path, "audio", ["audio/x-mpegurl"])


def file_is_image(file_path: str) -> bool:
    """Returns true if the given file is a readable image file"""
    return file_is_type(file_path, "image")


def resource_path(relative_path: str) -> str:
    return str(Path(__file__).parent.parent / relative_path)
