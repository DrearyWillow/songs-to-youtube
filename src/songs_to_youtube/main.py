import atexit
import glob
import os
import posixpath
import shutil
import sys
from contextlib import suppress
from typing import TYPE_CHECKING, cast

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QAction, QIcon, QRegion
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QWidget,
)

from songs_to_youtube.const import APPLICATION, ORGANIZATION, VERSION
from songs_to_youtube.field import APPLICATION_IMAGES, SETTINGS_VALUES
from songs_to_youtube.log import LogWidget, applogger
from songs_to_youtube.progress_window import ProgressWindow
from songs_to_youtube.settings import AddUserWindow, SettingsWindow, get_setting, get_settings
from songs_to_youtube.song_settings_widget import SongSettingsWidget
from songs_to_youtube.song_tree_widget import SongTreeWidget
from songs_to_youtube.utils import YouTubeLogin, load_ui, resource_path

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMenu, QMenuBar, QPushButton, QStatusBar

    class MainWindowUI(QMainWindow):
        treeWidget: SongTreeWidget
        renderButton: QPushButton
        cancelButton: QPushButton
        songSettingsWindow: SongSettingsWidget
        logWindow: LogWidget
        progressScrollArea: QScrollArea
        progressWindow: ProgressWindow

        menubar: QMenuBar
        menuFile: QMenu
        menuImport: QMenu
        statusbar: QStatusBar

        actionSettings: QAction
        actionAlbums: QAction
        actionSongs: QAction
        actionAbout: QAction


class MainWindow(QMainWindow):
    DEFAULT_QPOINT = QtCore.QPoint()
    DEFAULT_QREGION = QRegion()

    def __init__(self, first_time=False):
        super().__init__()
        self.ui = cast(
            MainWindowUI,
            load_ui("mainwindow.ui", (SongSettingsWidget, SongTreeWidget, LogWidget, ProgressWindow)),
        )
        self.first_time = first_time
        self.ui.cancelButton.setVisible(False)
        self.connect_actions()
        self.setAcceptDrops(True)
        self.renderer = None
        self.uploader = None
        self.cancelled = False

    def load_albums(self):
        file_dialog = QFileDialog(self, "Import Albums")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        file_view = file_dialog.findChild(QtWidgets.QListView, "listView")

        if file_view:
            file_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        f_tree_view = file_dialog.findChild(QtWidgets.QTreeView)
        if f_tree_view:
            f_tree_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        if file_dialog.exec() == QDialog.DialogCode.Accepted:
            paths = file_dialog.selectedFiles()
            for album in paths:
                self.ui.treeWidget.addAlbum(album)

    def on_upload_finished(self, results):
        self.ui.treeWidget.setEnabled(True)
        self.ui.cancelButton.setVisible(False)
        self.ui.renderButton.setVisible(True)
        if self.cancelled:
            applogger.error("Upload cancelled")
            # delete rendered/partially-rendered videos
            for path in results:
                with suppress(OSError):
                    os.remove(path)
            self.cancelled = False
        else:
            applogger.success("%d/%d uploads successful", (sum(int(s) for s in results.values()), len(results)))
            self.uploader = None
            if get_setting("deleteAfterUploading") == SETTINGS_VALUES.CheckBox.CHECKED:
                for path, success in results.items():
                    if success:
                        os.remove(path)
            # remove successful uploads
            self.ui.treeWidget.remove_by_file_paths({path for path in results if results[path]})

    def on_render_finished(self, results):
        if self.cancelled:
            applogger.error("Render cancelled")
            self.on_upload_finished(results)
        else:
            applogger.success("%d/%d renders successful", (sum(int(s) for s in results.values()), len(results)))
            # remove successful renders that will not be uploaded
            self.ui.treeWidget.remove_by_file_paths({path for path in results if results[path]}, False)
            # upload to youtube;
            self.uploader = self.ui.treeWidget.get_uploader(results)
            self.uploader.finished.connect(self.on_upload_finished)
            self.ui.progressWindow.on_upload_start(self.uploader)
            self.uploader.upload()
        self.renderer = None

    def render(
        self,
        target: QtGui.QPaintDevice | QtGui.QPainter,
        targetOffset: QtCore.QPoint = DEFAULT_QPOINT,
        sourceRegion: QtGui.QRegion | QtGui.QBitmap | QtGui.QPolygon | QtCore.QRect = DEFAULT_QREGION,
        renderFlags: QWidget.RenderFlag = (QWidget.RenderFlag.DrawWindowBackground | QWidget.RenderFlag.DrawChildren),
    ) -> None:
        self.ui.treeWidget.setEnabled(False)
        self.ui.cancelButton.setVisible(True)
        self.ui.renderButton.setVisible(False)
        self.renderer = self.ui.treeWidget.get_renderer()
        self.renderer.finished.connect(self.on_render_finished)
        self.ui.progressWindow.on_render_start(self.renderer)
        self.renderer.render()

    def cancel(self):
        self.cancelled = True
        if self.renderer:
            self.renderer.cancel()
            self.ui.treeWidget.setEnabled(True)
            self.ui.cancelButton.setVisible(False)
            self.ui.renderButton.setVisible(True)
        if self.uploader:
            self.uploader.cancel()

    def load_songs(self):
        file_names = QFileDialog.getOpenFileNames(self, "Import Songs")[0]
        for file in file_names:
            self.ui.treeWidget.addSong(file)

    def open_settings(self):
        window = SettingsWindow(self)
        window.settings_changed.connect(self.ui.logWindow.update_settings)
        window.show()

    def about(self):
        QMessageBox.about(self, APPLICATION, f"{VERSION}\nMade by {ORGANIZATION}")

    def show(self):
        self.ui.show()
        if (
            get_setting("uploadYouTube") == SETTINGS_VALUES.CheckBox.CHECKED
            and len(YouTubeLogin.get_all_usernames()) == 0
        ):
            msg_box = QMessageBox.warning(
                self,
                "Warning",
                "No users detected, but upload to YouTube is the default. Add new user for uploading?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if msg_box == QMessageBox.StandardButton.Ok:
                self.msg_box = AddUserWindow()
                self.msg_box.show()

    def connect_actions(self):
        self.ui.actionAbout.triggered.connect(self.about)
        self.ui.actionAlbums.triggered.connect(self.load_albums)
        self.ui.actionSongs.triggered.connect(self.load_songs)
        self.ui.actionSettings.triggered.connect(self.open_settings)
        self.ui.treeWidget.selectionModel().selectionChanged.connect(
            self.ui.songSettingsWindow.song_tree_selection_changed
        )
        self.ui.renderButton.clicked.connect(self.render)
        self.ui.cancelButton.clicked.connect(self.cancel)


def main():
    # no idea why this is necessary but it is... otherwise
    # future calls to QUiLoader completely freeze the app
    _ = QUiLoader()
    # initialize default settings
    settings_path = get_settings().fileName()
    if not os.path.exists(settings_path):
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        shutil.copy(resource_path("config/default.ini"), settings_path)

    os.makedirs(posixpath.join(QtCore.QDir().tempPath(), APPLICATION), exist_ok=True)

    def clean_up():
        for file in glob.glob(posixpath.join(QtCore.QDir().tempPath(), APPLICATION, "*")):
            os.remove(file)

    atexit.register(clean_up)
    app = QApplication([])
    app.setWindowIcon(QIcon(APPLICATION_IMAGES[":/image/icon.ico"]))
    app.setOrganizationName(ORGANIZATION)
    app.setApplicationName(APPLICATION)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
