import time
from pathlib import Path
from typing import Final, Iterator

import pytest

import sampletones_application.services.folder_scan.service as scan_module
from tests.suite.screens.holds.constants import RELEASE_POLL_SECONDS
from tests.suite.screens.holds.signal import ReleaseSignal

HELD_ENTRY: Final[str] = "held-entry.txt"


class ScanHold:
    """Stands in for the walk a folder scan reads, holding every scan once the tree is read until released.

    The walk meets every entry the folder holds, and then goes on meeting an entry that is no
    recording, one every ``interval`` seconds, as a tree of thousands of other files would, until the
    scenario lets it end. A reader's Stop is checked between entries, so it is heard while the scan
    is held, as soon as the next entry comes.
    """

    def __init__(
        self,
        signal: ReleaseSignal,
        *,
        interval: float,
    ) -> None:
        self._signal = signal
        self._interval = interval

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Replaces the folder walk of a scan with the held one."""
        monkeypatch.setattr(scan_module, "walk_entries", self._walk)

    def release(self) -> None:
        """Lets the held walk end."""
        self._signal.release()

    def _walk(self, root: Path) -> Iterator[Path]:
        """Yields every entry below ``root``, then one more entry every ``interval`` seconds until released."""
        yield from root.rglob("*")
        while not self._signal.is_released():
            yield root / HELD_ENTRY
            time.sleep(self._interval)


class WindingDownScanHold:
    """Stands in for the walk a folder scan reads, keeping it past its last entry until released.

    The walk meets every entry the folder holds and then waits for the scenario, meeting no further entry. A
    reader's Stop is checked between entries, so a stopped read winds down for as long as the scenario holds
    it, and a folder asked for meanwhile arrives while it winds down on any machine.
    """

    def __init__(self, signal: ReleaseSignal) -> None:
        self._signal = signal

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Replaces the folder walk of a scan with the held one."""
        monkeypatch.setattr(scan_module, "walk_entries", self._walk)

    def release(self) -> None:
        """Lets the held walk end."""
        self._signal.release()

    def _walk(self, root: Path) -> Iterator[Path]:
        """Yields every entry below ``root``, then waits for the release before the walk ends."""
        yield from root.rglob("*")
        while not self._signal.is_released():
            time.sleep(RELEASE_POLL_SECONDS)
