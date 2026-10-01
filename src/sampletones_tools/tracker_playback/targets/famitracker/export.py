import subprocess
from pathlib import Path
from typing import Final

from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import FamiTrackerProgram

EXPORT_TIMEOUT_SECONDS: Final[int] = 120
NO_LOG: Final[str] = "FamiTracker wrote no log."


def export_nsf(
    program: FamiTrackerProgram,
    module: Path,
    nsf: Path,
    log: Path,
) -> None:
    """Has FamiTracker export a module to an NSF from its command line.

    FamiTracker quits the same way whether the export worked or not, so the NSF it leaves is what
    tells the two apart. A file at ``nsf`` from an earlier run is removed first.

    Args:
        program: FamiTracker, as this system runs it.
        module: The `.ftm` module to export.
        nsf: Where the NSF is written.
        log: Where FamiTracker writes what it did.

    Raises:
        FamiTrackerError: If FamiTracker writes no NSF or runs past ``EXPORT_TIMEOUT_SECONDS``, with its log.
    """
    nsf.unlink(missing_ok=True)
    try:
        completed = subprocess.run(
            program.export_command(module, nsf, log),
            env=program.environment(),
            capture_output=True,
            text=True,
            timeout=EXPORT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise FamiTrackerError(
            f"FamiTracker ran for more than {EXPORT_TIMEOUT_SECONDS} seconds exporting {module}"
        ) from error

    if not nsf.is_file():
        raise FamiTrackerError(f"FamiTracker wrote no NSF for {module}.\n{log_text(log)}\n{completed.stderr}".rstrip())


def log_text(log: Path) -> str:
    """What FamiTracker wrote to its log, or ``NO_LOG`` where it wrote none."""
    if not log.is_file():
        return NO_LOG

    return log.read_text(encoding="utf-8", errors="replace").strip()
