import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.output import OutputSettings, Playback

from .listener import StormListener
from .source import StormMark, StormSource


@dataclass(frozen=True)
class Entry:
    """One thing an owner did, and how the output answered."""

    owner: str
    operation: str
    outcome: str


@dataclass(frozen=True)
class Sounding:
    """A sound the output took: the playback its owner holds, what hears of it, and what it reads from."""

    playback: Playback[StormMark]
    listener: StormListener
    source: StormSource
    rank: int


@dataclass(frozen=True)
class Checkpoint:
    """Claims the owners made at once, and where each one stood once every one of them was decided.

    Attributes:
        ranks: The rank of each claim.
        held: Whether each claim held the output, or ``None`` for a claim the output declined.
    """

    ranks: Tuple[int, ...]
    held: Tuple[Optional[bool], ...]


class StormRecord:
    """Everything the storm's owners did and everything the output took, kept for the checks that follow.

    It also holds what every owner reads before a device change: the devices the backend listed last and the
    settings an owner applied last.
    """

    def __init__(self, seed: int, *, catalog: DeviceCatalog, settings: OutputSettings) -> None:
        self.seed = seed
        self._lock = threading.Lock()
        self._entries: List[Entry] = []
        self._soundings: List[Sounding] = []
        self._checkpoints: List[Checkpoint] = []
        self._catalog = catalog
        self._settings = settings
        self._identities: int = 0

    @property
    def entries(self) -> List[Entry]:
        with self._lock:
            return list(self._entries)

    @property
    def soundings(self) -> List[Sounding]:
        with self._lock:
            return list(self._soundings)

    @property
    def checkpoints(self) -> List[Checkpoint]:
        with self._lock:
            return list(self._checkpoints)

    @property
    def catalog(self) -> DeviceCatalog:
        with self._lock:
            return self._catalog

    @property
    def settings(self) -> OutputSettings:
        with self._lock:
            return self._settings

    def next_identity(self) -> int:
        with self._lock:
            self._identities += 1
            return self._identities

    def log(self, owner: str, operation: str, outcome: str) -> None:
        with self._lock:
            self._entries.append(Entry(owner=owner, operation=operation, outcome=outcome))

    def keep(self, sounding: Sounding) -> None:
        with self._lock:
            self._soundings.append(sounding)

    def checkpoint(self, checkpoint: Checkpoint) -> None:
        with self._lock:
            self._checkpoints.append(checkpoint)

    def refreshed(self, catalog: DeviceCatalog) -> None:
        """Takes the devices a refreshed backend lists, as the refresh's listener."""
        with self._lock:
            self._catalog = catalog

    def configured(self, settings: OutputSettings) -> None:
        with self._lock:
            self._settings = settings
