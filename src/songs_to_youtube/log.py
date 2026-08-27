import logging
import sys
import traceback
from collections.abc import Mapping
from types import TracebackType
from typing import ClassVar

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTextEdit, QWidget

from songs_to_youtube.const import APPLICATION
from songs_to_youtube.settings import get_setting

SUCCESS = 60


type SysExcInfoType = tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None]
type ExcInfoType = bool | SysExcInfoType | BaseException | None
type ArgsType = tuple[object, ...] | Mapping[str, object]


class SuccessLogger(logging.Logger):
    def success(
        self,
        message: object,
        *args: ArgsType,
        exc_info: ExcInfoType = None,
        extra: dict[str, object] | None = None,
        stack: bool = False,
        stacklevel: int = 1,
    ) -> None:
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, message, args, exc_info=exc_info, extra=extra, stack_info=stack, stacklevel=stacklevel)


logging.addLevelName(SUCCESS, "SUCCESS")

applogger = SuccessLogger(APPLICATION)


def convert_log_level(level: str) -> str | int:
    """Converts from LogLevel combobox text to Python log level value"""
    return getattr(logging, level)


class LogWidgetFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).strip()


class LogWidgetLogger(logging.Handler):
    COLORS: ClassVar[dict[str, QColor]] = {
        "WARNING": QColor("orange"),
        "INFO": QColor("black"),
        "DEBUG": QColor("blue"),
        "CRITICAL": QColor("red"),
        "ERROR": QColor("red"),
        "SUCCESS": QColor("green"),
    }

    def __init__(self, parent: QTextEdit) -> None:
        super().__init__()
        self.widget = parent
        self.widget.setReadOnly(True)

    def emit(self, record: logging.LogRecord) -> None:
        color = self.COLORS[record.levelname]
        self.widget.setTextColor(color)
        self.widget.append(self.format(record))
        self.widget.verticalScrollBar().setValue(self.widget.verticalScrollBar().maximum())


class LogWidget(QTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        log_handler = LogWidgetLogger(self)
        log_handler.setFormatter(LogWidgetFormatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S"))
        applogger.addHandler(log_handler)
        applogger.setLevel(logging.INFO)
        sys.excepthook = self.exception_handler
        self.update_settings()

    @staticmethod
    def exception_handler(exc_type: type[BaseException], value: BaseException, trace: TracebackType) -> None:
        applogger.error("".join(traceback.format_tb(trace)))
        applogger.error("%s %s", exc_type, value)
        sys.__excepthook__(exc_type, value, trace)

    @staticmethod
    def update_settings() -> None:
        try:
            new_level = convert_log_level(get_setting("logLevel"))
        except (ValueError, AttributeError):
            new_level = logging.ERROR
        applogger.setLevel(new_level)
