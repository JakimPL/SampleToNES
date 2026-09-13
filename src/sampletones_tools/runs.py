from datetime import UTC, datetime
from pathlib import Path
from typing import Final

RUN_STAMP: Final[str] = "run-%Y%m%d-%H%M%S"


def stamped_run_directory(root: Path) -> Path:
    """The directory a measurement run lands in under ``root``, named by the moment it starts.

    The stamp is UTC and sorts by name, so the runs under one root read in the order they ran.

    Args:
        root: The directory the runs of one measurement share.

    Returns:
        Path: The run's directory, which the run creates.
    """
    return root / datetime.now(UTC).strftime(RUN_STAMP)
