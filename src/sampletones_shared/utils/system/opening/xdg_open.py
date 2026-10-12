import subprocess
from pathlib import Path
from typing import Final

from sampletones_shared.utils.system.programs import program_environment

XDG_OPEN: Final[str] = "xdg-open"


class XdgOpenFileOpener:
    """Shows a file through ``xdg-open``, which hands it to the desktop's program for its kind.

    ``xdg-open`` starts in a session of its own, so the program it starts outlives the
    application, and it starts with the reader's own library path, so a browser started from a
    bundle loads the system's libraries.
    """

    def open(self, path: Path) -> None:
        subprocess.Popen(  # pylint: disable=consider-using-with
            [XDG_OPEN, str(path)],
            env=program_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
