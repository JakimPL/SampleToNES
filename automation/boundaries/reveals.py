import os
import stat
from pathlib import Path
from typing import Final, Mapping, Tuple

import pytest

PATH_VARIABLE: Final[str] = "PATH"
FILE_MANAGER: Final[str] = "nemo"
FILE_MANAGER_ENTRY: Final[str] = f"{FILE_MANAGER}.desktop"
EXECUTABLE: Final[int] = stat.S_IRWXU


class FileManagerStandIn:
    """Stands in for the desktop's file manager and its handler of files, noting every path the
    application hands them.

    The application asks ``xdg-mime`` which file manager the desktop uses and then asks that file
    manager, or ``xdg-open``, to show a path, and it asks ``xdg-open`` to open a page in the
    browser. Programs of those names lie in ``folder``, which leads the search path, so the
    application's own code runs and reaches them: the first names a file manager they stand for,
    the file manager writes the path it was given to ``shown_log``, and ``xdg-open`` writes a folder
    there and a file to ``opened_log``, one line each.
    """

    def __init__(
        self,
        folder: Path,
        shown_log: Path,
        opened_log: Path,
    ) -> None:
        self.folder = folder
        self._shown_log = shown_log
        self._opened_log = opened_log

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Lays the programs in the folder and puts the folder first on the search path."""
        self.folder.mkdir(parents=True, exist_ok=True)
        for name, script in self._programs().items():
            program = self.folder / name
            program.write_text(script)
            program.chmod(EXECUTABLE)

        monkeypatch.setenv(
            PATH_VARIABLE,
            os.pathsep.join((str(self.folder), os.environ[PATH_VARIABLE])),
        )

    def shown(self) -> Tuple[Path, ...]:
        """Every path the file manager was asked to show, in order."""
        return _noted(self._shown_log)

    def opened(self) -> Tuple[Path, ...]:
        """Every file handed to the desktop's program for its kind, in order."""
        return _noted(self._opened_log)

    def _programs(self) -> Mapping[str, str]:
        noting = f'#!/bin/sh\nfor path in "$@"; do printf \'%s\\n\' "$path" >> "{self._shown_log}"; done\n'
        sorting = (
            "#!/bin/sh\n"
            'for path in "$@"; do\n'
            f'  if [ -d "$path" ]; then log="{self._shown_log}"; else log="{self._opened_log}"; fi\n'
            '  printf \'%s\\n\' "$path" >> "$log"\n'
            "done\n"
        )
        return {
            "xdg-mime": f"#!/bin/sh\necho {FILE_MANAGER_ENTRY}\n",
            FILE_MANAGER: noting,
            "xdg-open": sorting,
        }


def _noted(log: Path) -> Tuple[Path, ...]:
    if not log.exists():
        return ()

    return tuple(Path(line) for line in log.read_text().splitlines())
