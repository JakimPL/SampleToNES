from datetime import UTC, datetime
from pathlib import Path
from typing import Final

RUN_STAMP: Final[str] = "run-%Y%m%d-%H%M%S"
BOARD_STAMP: Final[str] = "page-%Y%m%d-%H%M%S"


def stamped_run_directory(root: Path) -> Path:
    """The directory a measurement run lands in under ``root``, named by the moment it starts.

    Args:
        root: The directory the runs of one measurement share.

    Returns:
        Path: The run's directory, which the run creates.
    """
    return stamped_directory(root, RUN_STAMP)


def stamped_board_directory(root: Path) -> Path:
    """The directory a page comparing runs lands in under ``root``, named by the moment it is built.

    Args:
        root: The directory the pages of one measurement share.

    Returns:
        Path: The page's directory, which the build creates.
    """
    return stamped_directory(root, BOARD_STAMP)


def stamped_directory(root: Path, stamp: str) -> Path:
    """The directory of one moment under ``root``, named by the stamp it is given.

    The stamp is UTC and sorts by name, so the directories under one root read in the order they
    were made.

    Args:
        root: The directory the results of one measurement share.
        stamp: The ``strftime`` pattern the directory is named by.

    Returns:
        Path: The directory, which its writer creates.
    """
    return root / datetime.now(UTC).strftime(stamp)
