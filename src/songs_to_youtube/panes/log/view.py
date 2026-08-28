from typing import ClassVar

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTextEdit, QWidget


class LogView(QTextEdit):
    COLORS: ClassVar[dict[str, QColor]] = {
        "WARNING": QColor("orange"),
        "INFO": QColor("black"),
        "DEBUG": QColor("blue"),
        "CRITICAL": QColor("red"),
        "ERROR": QColor("red"),
        "SUCCESS": QColor("green"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)

    def print_log(self, log: str, levelname: str) -> None:
        color = self.COLORS[levelname]
        self.setTextColor(color)
        self.append(log)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
