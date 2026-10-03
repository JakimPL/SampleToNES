from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union


@dataclass(frozen=True, eq=False)
class FolderScanRequest:
    """One folder a reader asked to have read.

    A request is told apart from every other one by its identity, so a report from a reading the
    reader gave up on reads as late, even where the next reading is of the same folder.

    Attributes:
        root: The folder whose recordings are read.
    """

    root: Path


@dataclass(frozen=True)
class FolderScanStarted:
    """The reading of a folder has begun."""

    request: FolderScanRequest


@dataclass(frozen=True)
class FolderScanProgress:
    """How many recordings the reading has met so far."""

    request: FolderScanRequest
    count: int


@dataclass(frozen=True)
class FolderScanSuccess:
    """Every recording below the folder, in name order."""

    request: FolderScanRequest
    recordings: Tuple[Path, ...]


@dataclass(frozen=True, eq=False)
class FolderScanError:
    """A reading that failed partway, with the failure it raised."""

    request: FolderScanRequest
    exception: Exception


@dataclass(frozen=True)
class FolderScanCanceled:
    """A reading that gave up at the reader's Stop."""

    request: FolderScanRequest


FolderScanResult = Union[
    FolderScanStarted,
    FolderScanProgress,
    FolderScanSuccess,
    FolderScanError,
    FolderScanCanceled,
]
