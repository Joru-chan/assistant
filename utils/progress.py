from __future__ import annotations

import itertools
import subprocess
import sys
import threading
import time
from typing import Iterable, Tuple


def log(message: str, verbose: bool = False, stream=sys.stderr) -> None:
    if verbose:
        print(message, file=stream)


def print_step(message: str, stream=sys.stderr) -> None:
    print(f"-> {message}", file=stream)


def print_ok(message: str, stream=sys.stderr) -> None:
    print(f"OK: {message}", file=stream)


def print_warn(message: str, stream=sys.stderr) -> None:
    print(f"WARN: {message}", file=stream)


class Spinner:
    def __init__(self, label: str, enabled: bool = True) -> None:
        self.label = label
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _spin(self) -> None:
        for ch in itertools.cycle("|/-\\"):
            if self._stop.is_set():
                break
            sys.stderr.write(f"\r{self.label} {ch}")
            sys.stderr.flush()
            time.sleep(0.1)

    def __enter__(self) -> "Spinner":
        if self.enabled:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.enabled:
            self._stop.set()
            if self._thread:
                self._thread.join()
            sys.stderr.write("\r" + " " * (len(self.label) + 4) + "\r")
            sys.stderr.flush()


def _stream_lines(stream) -> Iterable[str]:
    for line in iter(stream.readline, ""):
        yield line


def run_command(
    command: list[str],
    *,
    label: str,
    verbose: bool = False,
    progress: bool = True,
) -> Tuple[int, str]:
    buffer: list[str] = []
    with Spinner(label, enabled=progress):
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in _stream_lines(proc.stdout):
            buffer.append(line)
            if verbose:
                sys.stderr.write(line)
        proc.stdout.close()
        returncode = proc.wait()
    return returncode, "".join(buffer)
