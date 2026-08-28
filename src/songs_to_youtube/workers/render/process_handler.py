import atexit
import os
import subprocess
from contextlib import suppress
from queue import Queue
from threading import Thread
from typing import IO

import psutil
from PySide6.QtCore import QObject, Signal

PROCESSES: list[subprocess.Popen[bytes]] = []


# make sure to stop all the ffmpeg processes from running
# if we close the application
def clean_up() -> None:
    for p in PROCESSES:
        with suppress(Exception):
            process = psutil.Process(p.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()


atexit.register(clean_up)


class ProcessHandler(QObject):
    stdout = Signal(str)
    stderr = Signal(str)

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def read_pipe(pipe: IO[bytes], queue: Queue[tuple[IO[bytes] | None, str | None]]) -> None:
        try:
            with pipe:
                for line in iter(pipe.readline, b""):
                    queue.put((pipe, line.decode("utf-8")))
        finally:
            queue.put((None, None))

    def run(self, command: str) -> int:
        if os.name == "nt":
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True,
            )
        else:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )

        PROCESSES.append(process)
        queue: Queue[tuple[IO[bytes] | None, str | None]] = Queue()
        Thread(target=self.read_pipe, args=[process.stdout, queue]).start()
        Thread(target=self.read_pipe, args=[process.stderr, queue]).start()
        while True:
            pipe, line = queue.get()
            if pipe is None:
                break
            if pipe == process.stdout:
                self.stdout.emit(line)
            else:
                self.stderr.emit(line)
        error = process.wait() != 0
        PROCESSES.remove(process)
        return error
