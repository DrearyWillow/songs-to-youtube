import logging
import sys
import traceback
from types import TracebackType

from songs_to_youtube.applogger import applogger
from songs_to_youtube.components.log.handler import LogHandler
from songs_to_youtube.components.log.view import LogView
from songs_to_youtube.settings import get_setting


class LogPresenter:
    def __init__(self) -> None:
        self.view = LogView()
        log_handler = LogHandler(self.view)
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
            # Converts from LogLevel combobox text to Python log level value
            new_level = getattr(logging, get_setting("logLevel"))
        except (ValueError, AttributeError):
            new_level = logging.INFO
        applogger.setLevel(new_level)
