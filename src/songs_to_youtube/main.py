import atexit
import shutil
import sys
from contextlib import suppress
from pathlib import Path
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

from songs_to_youtube.applogger import applogger
from songs_to_youtube.const import APPLICATION, ORGANIZATION, VERSION
from songs_to_youtube.dialogs.add_user.add_user import AddUserWindow
from songs_to_youtube.dialogs.settings.presenter import SettingsWindowPresenter
from songs_to_youtube.panes.detail.presenter import DetailPanePresenter
from songs_to_youtube.panes.detail.view import DetailPaneView
from songs_to_youtube.panes.log.presenter import LogPanePresenter
from songs_to_youtube.panes.log.view import LogPaneView
from songs_to_youtube.panes.progress.presenter import ProgressPanePresenter
from songs_to_youtube.panes.progress.view import ProgressPaneView
from songs_to_youtube.panes.tree.tree_widget import SongTreeWidget
from songs_to_youtube.utils import get_all_usernames, get_setting, get_settings, load_ui, resource_path
from songs_to_youtube.utils.misc import APPLICATION_IMAGES, SETTINGS_VALUES

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMenu, QMenuBar, QPushButton, QStatusBar

    class MainWindowUI(QMainWindow):
        # TODO: need to fix main window ui
        treeWidget: SongTreeWidget
        renderButton: QPushButton
        cancelButton: QPushButton
        detailPaneView: DetailPaneView
        logPaneView: LogPaneView
        progressScrollArea: QScrollArea
        progressPaneView: ProgressPaneView

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

    def __init__(self, *, first_time: bool = False) -> None:
        super().__init__()
        self.ui = cast(
            "MainWindowUI",
            # TODO: need to fix ui file
            load_ui("mainwindow.ui", (DetailPaneView, SongTreeWidget, LogPaneView, ProgressPaneView)),
        )

        self.detail_presenter = DetailPanePresenter(self.ui.detailPaneView)
        self.log_presenter = LogPanePresenter(self.ui.logPaneView)
        self.progress_presenter = ProgressPanePresenter(self.ui.progressPaneView)

        self.first_time = first_time
        self.ui.cancelButton.setVisible(False)
        self.connect_actions()
        self.setAcceptDrops(True)
        self.renderer = None
        self.uploader = None
        self.cancelled = False

    def load_albums(self) -> None:
        file_dialog = QFileDialog(self, "Import Albums")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setOption(QFileDialog.Option.ShowDirsOnly, on=True)
        file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, on=True)
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

    def on_upload_finished(self, results: dict[str, bool]) -> None:
        self.ui.treeWidget.setEnabled(True)
        self.ui.cancelButton.setVisible(False)
        self.ui.renderButton.setVisible(True)
        if self.cancelled:
            applogger.error("Upload cancelled")
            # delete rendered/partially-rendered videos
            for path in results:
                with suppress(OSError):
                    Path(path).unlink()
            self.cancelled = False
        else:
            applogger.success("%d/%d uploads successful", (sum(int(s) for s in results.values()), len(results)))
            self.uploader = None
            if get_setting("deleteAfterUploading") == SETTINGS_VALUES.CheckBox.CHECKED:
                for path, success in results.items():
                    if success:
                        Path(path).unlink()
            # remove successful uploads
            self.ui.treeWidget.remove_by_file_paths({path for path in results if results[path]})

    def on_render_finished(self, results: dict[str, bool]) -> None:
        if self.cancelled:
            applogger.error("Render cancelled")
            self.on_upload_finished(results)
        else:
            applogger.success("%d/%d renders successful", (sum(int(s) for s in results.values()), len(results)))
            # remove successful renders that will not be uploaded
            self.ui.treeWidget.remove_by_file_paths({path for path in results if results[path]}, uploaded=False)
            # upload to youtube;
            self.uploader = self.ui.treeWidget.get_uploader(results)
            self.uploader.finished.connect(self.on_upload_finished)
            self.progress_presenter.on_upload_start(self.uploader)
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
        self.progress_presenter.on_render_start(self.renderer)
        self.renderer.render()

    def cancel(self) -> None:
        self.cancelled = True
        if self.renderer:
            self.renderer.cancel()
            self.ui.treeWidget.setEnabled(True)
            self.ui.cancelButton.setVisible(False)
            self.ui.renderButton.setVisible(True)
        if self.uploader:
            self.uploader.cancel()

    def load_songs(self) -> None:
        file_names = QFileDialog.getOpenFileNames(self, "Import Songs")[0]
        for file in file_names:
            self.ui.treeWidget.addSong(file)

    def open_settings(self) -> None:
        window = SettingsWindowPresenter(self)
        window.settingsChanged.connect(self.log_presenter.update_settings)
        window.show()

    def about(self) -> None:
        QMessageBox.about(self, APPLICATION, f"{VERSION}\nMade by {ORGANIZATION}")

    def show(self) -> None:
        self.ui.show()
        if get_setting("uploadYouTube") == SETTINGS_VALUES.CheckBox.CHECKED and len(get_all_usernames()) == 0:
            msg_box = QMessageBox.warning(
                self,
                "Warning",
                "No users detected, but upload to YouTube is the default. Add new user for uploading?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if msg_box == QMessageBox.StandardButton.Ok:
                self.msg_box = AddUserWindow()
                self.msg_box.show()

    def connect_actions(self) -> None:
        self.ui.actionAbout.triggered.connect(self.about)
        self.ui.actionAlbums.triggered.connect(self.load_albums)
        self.ui.actionSongs.triggered.connect(self.load_songs)
        self.ui.actionSettings.triggered.connect(self.open_settings)
        self.ui.treeWidget.selectionModel().selectionChanged.connect(self.detail_presenter.song_tree_selection_changed)
        self.ui.renderButton.clicked.connect(self.render)
        self.ui.cancelButton.clicked.connect(self.cancel)


def main() -> None:
    # no idea why this is necessary but it is... otherwise
    # future calls to QUiLoader completely freeze the app
    _ = QUiLoader()
    # initialize default settings
    settings_file = Path(get_settings().fileName())
    if not settings_file.exists():
        settings_file.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(resource_path("config/default.ini"), settings_file)

    (Path(QtCore.QDir().tempPath()) / APPLICATION).mkdir(exist_ok=True, parents=True)

    def clean_up() -> None:
        for file_path in (Path(QtCore.QDir().tempPath()) / APPLICATION).glob("*"):
            if file_path.is_file() or file_path.is_symlink():
                file_path.unlink(missing_ok=True)
            elif file_path.is_dir():
                shutil.rmtree(file_path, ignore_errors=True)

    atexit.register(clean_up)
    app = QApplication([])
    app.setWindowIcon(QIcon(str(APPLICATION_IMAGES[":/assets/icon.ico"])))
    app.setOrganizationName(ORGANIZATION)
    app.setApplicationName(APPLICATION)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
