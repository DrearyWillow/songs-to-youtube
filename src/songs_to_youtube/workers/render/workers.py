import pathlib
import traceback
from contextlib import suppress
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QIODeviceBase, QObject, QRunnable, QTemporaryFile, Signal

from songs_to_youtube.workers.render.process_handler import ProcessHandler

if TYPE_CHECKING:
    from songs_to_youtube.panes.tree.widget_item.album import AlbumTreeWidgetItem
    from songs_to_youtube.panes.tree.widget_item.song import SongTreeWidgetItem

type SongWorker = RenderSongWorker | CombineSongWorker


class RenderWorkerSignals(QObject):
    finished = Signal(bool)
    error = Signal(str)
    progress = Signal(str)


class RenderSongWorker(QRunnable):
    def __init__(self, song: SongTreeWidgetItem, *, auto_delete: bool) -> None:
        super().__init__()
        self.auto_delete = auto_delete
        self.song = song
        self.name = self.song.get("fileOutput")
        self.signals = RenderWorkerSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            command_str = (self.song.get("commandString")).format(**self.song.to_dict())
            handler = ProcessHandler()
            handler.stderr.connect(self.signals.error.emit)
            handler.stdout.connect(self.signals.progress.emit)
            errors = handler.run(command_str)
            self.signals.finished.emit(not errors)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
            finished = False
            self.signals.finished.emit(finished)

    def get_duration_ms(self) -> float:
        return self.song.get_duration_ms()

    def __str__(self) -> str:
        return self.name


class CombineSongWorker(QRunnable):
    def __init__(self, album: AlbumTreeWidgetItem) -> None:
        super().__init__()
        self.auto_delete = True
        self.album = album
        self.name = self.album.get("fileOutput")
        self.signals = RenderWorkerSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            song_list = QTemporaryFile()
            song_list.open(
                QIODeviceBase.OpenModeFlag.WriteOnly
                | QIODeviceBase.OpenModeFlag.Append
                | QIODeviceBase.OpenModeFlag.Text
            )
            for song in self.album.getChildren():
                file_output = song.get("fileOutput").replace("'", "'\\''")
                file_str = f"file 'file:{file_output}'\n"
                song_list.write(QByteArray(file_str.encode()))
            song_list.close()
            command_str = self.album.get("concatCommandString").format(
                input_file_list=song_list.fileName(),
                fileOutputPath=self.album.get("fileOutput"),
            )
            handler = ProcessHandler()
            handler.stderr.connect(self.signals.error.emit)
            handler.stdout.connect(self.signals.progress.emit)
            errors = handler.run(command_str)
            self.signals.finished.emit(not errors)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
            finished = False
            self.signals.finished.emit(finished)
        finally:
            for song in self.album.getChildren():
                with suppress(OSError):
                    pathlib.Path(song.get("fileOutput")).unlink()

    def get_duration_ms(self) -> float:
        return self.album.get_duration_ms()

    def __str__(self) -> str:
        return self.name
