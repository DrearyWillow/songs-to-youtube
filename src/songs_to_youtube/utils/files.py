import os
from collections.abc import Iterable, Iterator
from pathlib import Path

from PySide6.QtCore import QDir, QDirIterator, QFileInfo, QMimeDatabase

from songs_to_youtube.applogger import applogger

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _GetShortPathNameW = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD

    def get_short_path_name(long_name: str) -> str:
        """
        Gets the short path name of a given long path.
        http://stackoverflow.com/a/23598461/200291
        """
        output_buf_size = 0
        while True:
            output_buf = ctypes.create_unicode_buffer(output_buf_size)
            needed = _GetShortPathNameW(long_name, output_buf, output_buf_size)
            if needed == 0:
                raise ctypes.WinError(ctypes.get_last_error())
            if output_buf_size >= needed:
                return output_buf.value
            output_buf_size = needed


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
    return str(Path(__file__).parent / relative_path)
