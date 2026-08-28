from PySide6.QtCore import QObject, Signal


class WorkerBaseClass(QObject):
    finished = Signal(dict[str, bool])
    worker_progress = Signal(str, int)
    worker_error = Signal(str, str)
    worker_done = Signal(str, bool)
