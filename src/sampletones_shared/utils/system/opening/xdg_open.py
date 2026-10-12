import subprocess
from pathlib import Path
from typing import Dict, Final, Mapping

XDG_OPEN: Final[str] = "xdg-open"
LIBRARY_PATH: Final[str] = "LD_LIBRARY_PATH"
ORIGINAL_LIBRARY_PATH: Final[str] = "LD_LIBRARY_PATH_ORIG"


class XdgOpenFileOpener:
    """Shows a file through ``xdg-open``, which hands it to the desktop's program for its kind.

    ``xdg-open`` starts in a session of its own, so the program it starts outlives the
    application. A PyInstaller bundle points ``LD_LIBRARY_PATH`` at the libraries it carries and
    keeps the reader's own value in ``LD_LIBRARY_PATH_ORIG``; the program receives the reader's
    value, or none where the reader set none, so it loads the system's libraries.
    """

    def __init__(
        self,
        environment: Mapping[str, str],
        *,
        frozen: bool,
    ) -> None:
        self._environment = environment
        self._frozen = frozen

    def open(self, path: Path) -> None:
        subprocess.Popen(  # pylint: disable=consider-using-with
            [XDG_OPEN, str(path)],
            env=self.child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def child_environment(self) -> Dict[str, str]:
        """The variables ``xdg-open`` starts with: the application's, with the reader's library path."""
        environment = dict(self._environment)
        if not self._frozen:
            return environment

        original = environment.pop(ORIGINAL_LIBRARY_PATH, None)
        if original is None:
            environment.pop(LIBRARY_PATH, None)
        else:
            environment[LIBRARY_PATH] = original

        return environment
