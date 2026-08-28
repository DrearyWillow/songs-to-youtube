import logging

from songs_to_youtube.components.log.view import LogView


class LogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).strip()


class LogHandler(logging.Handler):
    def __init__(self, view: LogView) -> None:
        super().__init__()
        self.setFormatter(LogFormatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S"))
        self.view = view

    def emit(self, record: logging.LogRecord) -> None:
        levelname = record.levelname
        formatted = self.format(record)
        self.view.print_log(formatted, levelname)
