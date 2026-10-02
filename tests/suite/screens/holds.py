import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import AbstractSet, Final, Iterator, List, Protocol, Sequence

import pytest

import sampletones_application.logic.main.sources.scan as scan_module
import sampletones_core.reconstructions.converter.converter as converter_module
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.progress import STAGE_BEGUN, WHOLE_STAGE, ReconstructionReporter, announce
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.types.path import Pathlike
from tests.suite.conversion import COUNTED_STAGES, FAKE_FRAMES, HALFWAY

RELEASE_POLL_SECONDS: Final[float] = 0.05
HELD_ENTRY: Final[str] = "held-entry.txt"


class Hold(Protocol):
    """Work a scenario keeps under way until it lets go, so a gesture lands while the work runs."""

    def release(self) -> None:
        """Lets the work carry on to its end."""


class Holds:
    """Every hold a scenario put on the application's work, let go together before the scenario leaves.

    Leaving waits for work in flight, so the holds are released before the exit is asked for.
    """

    def __init__(self) -> None:
        self._holds: List[Hold] = []

    def add(self, hold: Hold) -> None:
        self._holds.append(hold)

    def release_all(self) -> None:
        for hold in self._holds:
            hold.release()


@dataclass(frozen=True)
class ReleaseSignal:
    """A file whose appearance lets held work carry on, which a worker process sees as well as the scenario."""

    path: Path

    def release(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def is_released(self) -> bool:
        return self.path.exists()


class HeldReconstructor:
    """A reconstructor that walks a run's stages, stops halfway through matching until released, and builds nothing.

    It decides when the run lands, never what it computes: the walk reports the stages a real
    reconstruction reports, and a run left with nothing built writes no file. While held it goes on
    announcing the halfway mark, which is where a run the reader stops unwinds, and it waits for as
    long as the scenario holds it.

    It travels to a worker with the job, the way the real one does, so it is built from a
    configuration and the channels the same way, with the release named beside them.
    """

    def __init__(
        self,
        config: Config,
        channels: AbstractSet[ChannelName],
        release_path: Path,
    ) -> None:
        self.config = config
        self.channels = channels
        self.release_path = release_path

    def reconstruct(
        self,
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
        *,
        report: ReconstructionReporter,
    ) -> None:
        """Walks the stages of a reconstruction, holding halfway through matching, and answers with nothing built.

        Raises:
            OperationCanceled: If the run is withdrawn while it is under way.
        """
        del paths, stems_config
        for stage in ReconstructionStage:
            if stage not in COUNTED_STAGES:
                announce(report, stage, STAGE_BEGUN, WHOLE_STAGE)
                continue

            for frame in range(FAKE_FRAMES + 1):
                announce(report, stage, frame, FAKE_FRAMES)
                if stage == ReconstructionStage.MATCHING and frame == HALFWAY:
                    self._hold(report, stage, frame)

    def _hold(
        self,
        report: ReconstructionReporter,
        stage: ReconstructionStage,
        frame: int,
    ) -> None:
        while not self.release_path.exists():
            announce(report, stage, frame, FAKE_FRAMES)
            time.sleep(RELEASE_POLL_SECONDS)


class ConversionHold:
    """Stands in for the converter's reconstructor with one that holds every run halfway until released."""

    def __init__(self, signal: ReleaseSignal) -> None:
        self._signal = signal

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            converter_module,
            "Reconstructor",
            partial(HeldReconstructor, release_path=self._signal.path),
        )

    def release(self) -> None:
        self._signal.release()


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
        monkeypatch.setattr(scan_module, "walk_entries", self._walk)

    def release(self) -> None:
        self._signal.release()

    def _walk(self, root: Path) -> Iterator[Path]:
        yield from root.rglob("*")
        while not self._signal.is_released():
            yield root / HELD_ENTRY
            time.sleep(self._interval)
