from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QPushButton,
)

from songs_to_youtube.utils import load_ui, save_user_cookies


class AddUserWindowUI(QDialog):
    buttonBox: QDialogButtonBox
    cookiesButton: QPushButton
    cookiesFile: QLineEdit
    username: QLineEdit


class AddUserWindow(QDialog):
    accepted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.ui = cast("AddUserWindowUI", load_ui("adduser.ui"))
        self.connect_actions()

    def connect_actions(self) -> None:
        self.ui.buttonBox.accepted.connect(self.accepted.emit)
        self.ui.buttonBox.accepted.connect(self.save_user)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.ui.cookiesButton.clicked.connect(self.open_cookies)

    def open_cookies(self) -> None:
        cookie_file = QFileDialog.getOpenFileName(
            self, "Select cookies.txt or json file", filter="Cookies (*.txt *.json)"
        )[0]
        if cookie_file:
            self.ui.cookiesFile.setText(cookie_file)

    def save_user(self) -> None:
        username = self.ui.username.text()
        cookie_file = self.ui.cookiesFile.text()
        save_user_cookies(username, cookie_file)

    def show(self) -> None:
        self.ui.show()
