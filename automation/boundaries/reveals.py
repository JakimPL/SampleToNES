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
    """Stands in for the desktop's file manager, noting every path the application asks it to show.

    The application asks ``xdg-mime`` which file manager the desktop uses and then asks that file
    manager, or ``xdg-open``, to show a path. Programs of those names lie in ``folder``, which leads
    the search path, so the application's own reveal code runs and reaches them: the first names a
    file manager they stand for, and the others write the path they were given to ``log``, one line
    each.
    """

    def __init__(
        self,
        folder: Path,
        log: Path,
    ) -> None:
        self.folder = folder
        self._log = log

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
        if not self._log.exists():
            return ()

        return tuple(Path(line) for line in self._log.read_text().splitlines())

    def _programs(self) -> Mapping[str, str]:
        noting = f'#!/bin/sh\nfor path in "$@"; do printf \'%s\\n\' "$path" >> "{self._log}"; done\n'
        return {
            "xdg-mime": f"#!/bin/sh\necho {FILE_MANAGER_ENTRY}\n",
            FILE_MANAGER: noting,
            "xdg-open": noting,
        }
