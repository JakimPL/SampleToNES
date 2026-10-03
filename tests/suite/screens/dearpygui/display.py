import shutil
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from pyvirtualdisplay.display import Display

KEEP_STATE_BETWEEN_CLIENTS: Final[str] = "-noreset"


class DisplayBackend(StrEnum):
    """The X server program a display runs on: Xvfb draws into memory, Xephyr into a window on the desktop."""

    XVFB = "xvfb"
    XEPHYR = "xephyr"

    @property
    def program(self) -> str:
        """The name of the X server program that draws for this backend."""
        return "Xvfb" if self is DisplayBackend.XVFB else "Xephyr"


class DisplayServerMissingError(RuntimeError):
    """Raised when the X server a run draws on is not installed."""


@dataclass(frozen=True)
class ScreenSize:
    """The pixels a display's screen spans."""

    width: int
    height: int


class VirtualDisplay:
    """An X server of a worker's own, which its scenarios draw on one after another.

    Xvfb draws into memory, which suits a run nobody watches. Xephyr draws into a window on the
    desktop, which lets a person follow a scenario as it plays. Either server takes every event a
    scenario sends, so the desktop around it stays untouched.

    The server goes on as it stands when its last client leaves. A server that resets then refuses
    the connection an application opens a moment after another of its clients closed, and each
    reset recompiles the keymap into output nobody reads, which stalls the server once that output
    fills its pipe.
    """

    def __init__(
        self,
        backend: DisplayBackend,
        size: ScreenSize,
    ) -> None:
        self._program = backend.program
        self._server = Display(
            backend=backend.value,
            size=(size.width, size.height),
            extra_args=[KEEP_STATE_BETWEEN_CLIENTS],
            manage_global_env=False,
        )

    def start(self) -> str:
        """Starts the server and returns the name a client connects to it under, such as ``:3``.

        Raises:
            DisplayServerMissingError: If the server's program is not installed.
        """
        if shutil.which(self._program) is None:
            raise DisplayServerMissingError(
                f"{self._program} is not installed. Install it from the system's packages, such as "
                f"the xvfb package on Debian and Ubuntu, to run the screen scenarios."
            )

        self._server.start()
        return self._server.new_display_var

    def stop(self) -> None:
        """Stops the server and frees the display name it served."""
        self._server.stop()
