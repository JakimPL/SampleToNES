import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Final, FrozenSet, List, Optional, Tuple

LIBRARY_PROBES: Final[FrozenSet[str]] = frozenset({"cc", "gcc", "ld", "ldconfig", "objdump"})
PROGRAM_ARGUMENT: Final[int] = 0
ARGUMENTS_ARGUMENT: Final[int] = 1
SPAWN_EVENTS: Final[FrozenSet[str]] = frozenset(
    {
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.startfile",
        "os.system",
        "subprocess.Popen",
        "webbrowser.open",
    }
)


class SpawnRefusedError(PermissionError):
    """Raised inside the application when it tries to start a program during a scenario."""


class SpawnGuard:
    """Refuses every program the application tries to start once a scenario runs, and remembers each try.

    A file manager, a browser or a dialog tool would open on the desktop around the scenario's display.
    The guard is an audit hook, so it stands in front of every way Python starts a program, however
    a module imported it. The application's own worker processes start through multiprocessing,
    which the hook leaves alone, and so are the tools ``ctypes.util.find_library`` asks where a
    shared library lies, and the stand-in programs of the folder the guard is told to allow. A
    refused try is remembered by its program and arguments alone, since the environment it carried
    can hold the secrets of the machine the run is on.
    """

    def __init__(self) -> None:
        self._refused: List[str] = []
        self._armed = False
        self._allowed: Optional[Path] = None
        self._lock = threading.Lock()

    def install(self) -> None:
        """Puts the guard in front of the process for good; it refuses nothing until armed."""
        sys.addaudithook(self._audit)

    def allow(self, folder: Path) -> None:
        """Lets the programs lying in ``folder`` start, which is where the scenario's stand-ins lie."""
        self._allowed = folder

    def arm(self) -> None:
        self._armed = True

    @property
    def refused(self) -> Tuple[str, ...]:
        with self._lock:
            return tuple(self._refused)

    def _audit(
        self,
        event: str,
        arguments: Tuple[Any, ...],
    ) -> None:
        if not self._armed or event not in SPAWN_EVENTS:
            return

        program = Path(str(arguments[PROGRAM_ARGUMENT])).name if arguments else ""
        if program in LIBRARY_PROBES or self._is_allowed(arguments):
            return

        attempt = f"{event} {program} {_described(arguments)}"
        with self._lock:
            self._refused.append(attempt)

        raise SpawnRefusedError(f"A screen scenario refuses to start a program: {attempt}")

    def _is_allowed(self, arguments: Tuple[Any, ...]) -> bool:
        """Whether the program a try names lies in the folder of stand-ins the guard allows."""
        if self._allowed is None or not arguments:
            return False

        located = shutil.which(str(arguments[PROGRAM_ARGUMENT]))
        return located is not None and Path(located).parent == self._allowed


def _described(arguments: Tuple[Any, ...]) -> str:
    if len(arguments) > ARGUMENTS_ARGUMENT:
        return repr(arguments[ARGUMENTS_ARGUMENT])

    return ""
