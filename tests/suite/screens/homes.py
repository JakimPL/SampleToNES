import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Final, Optional

from tests.suite.screens.paths import HOMES_PREFIX, PROCESSES_DIRECTORY

HIDDEN_PREFIX: Final[str] = "."
PROCESS_SEPARATOR: Final[str] = "-"


class HiddenHomesError(RuntimeError):
    """Raised when the temporary folder scenario homes would be made in lies inside a hidden folder."""


def make_worker_homes() -> Path:
    """Makes the temporary folder one worker keeps its scenario homes in, named after the worker's process.

    The application's browsers leave hidden folders out, so the homes need a temporary folder outside
    them. The folders that crashed workers left, whose process has gone, go first.

    Raises:
        HiddenHomesError: If the temporary folder lies inside a hidden folder.
    """
    parent = Path(tempfile.gettempdir())
    hidden = [part for part in parent.parts if part.startswith(HIDDEN_PREFIX)]
    if hidden:
        raise HiddenHomesError(
            f"Screen scenario homes are made in {parent}, which lies inside the hidden folder '{hidden[0]}', "
            "and the application's browsers leave hidden folders out. Point TMPDIR at a folder outside hidden "
            "folders."
        )

    _let_stale_homes_go(parent)
    return Path(tempfile.mkdtemp(prefix=f"{HOMES_PREFIX}{os.getpid()}{PROCESS_SEPARATOR}", dir=parent))


def let_go(folder: Path) -> None:
    """Removes ``folder``, opening first every folder inside it a scenario left locked."""
    reopen_folders(folder)
    shutil.rmtree(folder, ignore_errors=True)


def reopen_folders(top: Path) -> None:
    """Gives the owner back every folder under ``top``, so its files can be read, copied and removed.

    A scenario that locks a folder opens it again as it ends, and one that crashed or was stopped
    leaves it locked. A folder whose mode cannot change stays as it is, and the copy and the removal
    after it take what they can.
    """
    _open_to_owner(top)
    for folder, subfolders, _ in os.walk(top):
        for subfolder in subfolders:
            _open_to_owner(Path(folder) / subfolder)


def _open_to_owner(folder: Path) -> None:
    if folder.is_symlink():
        return

    try:
        folder.chmod(folder.stat().st_mode | stat.S_IRWXU)
    except OSError:
        return


def _let_stale_homes_go(parent: Path) -> None:
    """Removes the homes folders under ``parent`` whose worker process has gone, and keeps every other one.

    A worker removes its own folder as it ends, so a folder left behind belongs to a worker that crashed,
    or to a run still going. A folder whose name carries no process is left alone. Whether a process runs
    is read from the process folder Linux keeps, as the tier runs on Linux, so a machine without that
    folder keeps every homes folder.
    """
    if not PROCESSES_DIRECTORY.is_dir():
        return

    for folder in parent.glob(f"{HOMES_PREFIX}*"):
        process = _owner_process(folder)
        if process is not None and not _is_running(process):
            let_go(folder)


def _owner_process(folder: Path) -> Optional[int]:
    """The process id a homes folder's name carries before its separator, or ``None`` for a name that carries none.

    A temporary folder's random tail holds no separator, so a name made without a process reads as none.
    """
    process, separator, _ = folder.name.removeprefix(HOMES_PREFIX).partition(PROCESS_SEPARATOR)
    return int(process) if separator and process.isdigit() else None


def _is_running(process: int) -> bool:
    """Whether the process ``process`` names still runs, read from the process folder Linux keeps."""
    return (PROCESSES_DIRECTORY / str(process)).exists()
