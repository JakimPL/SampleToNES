import contextlib
import os
import sys
from typing import Final, Generator

from sampletones_shared.logger import logger

ALSA_PREFIX: Final[str] = "ALSA lib "


@contextlib.contextmanager
def captured_stderr() -> Generator[None, None, None]:
    """Routes what the native backend prints on standard error to the log while it starts or stops."""
    stderr_fd = sys.stderr.fileno()
    original_stderr_fd = os.dup(stderr_fd)

    read_pipe, write_pipe = os.pipe()
    os.dup2(write_pipe, stderr_fd)

    try:
        yield
    finally:
        os.dup2(original_stderr_fd, stderr_fd)
        os.close(original_stderr_fd)
        os.close(write_pipe)

        os.set_blocking(read_pipe, False)
        try:
            captured = os.read(read_pipe, 65536).decode("utf-8", errors="replace")
        except BlockingIOError:
            captured = ""
        os.close(read_pipe)

        for line in captured.strip().splitlines():
            if line.strip():
                logger.warning(f"ALSA: {line.replace(ALSA_PREFIX, '').strip()}")
