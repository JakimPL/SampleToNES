import webbrowser
from pathlib import Path

from sampletones_shared.exceptions import FileNotOpenedError


class BrowserFileOpener:
    """Shows a file through the standard library's ``webbrowser``, as a ``file://`` link.

    ``webbrowser`` reaches the system's own handler on Windows and macOS and the browsers it finds
    elsewhere, so it serves every system ``xdg-open`` is missing from.
    """

    def open(self, path: Path) -> None:
        if not webbrowser.open(path.resolve().as_uri()):
            raise FileNotOpenedError(f"No browser took {path}")
