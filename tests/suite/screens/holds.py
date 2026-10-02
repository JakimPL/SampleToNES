import itertools
import threading
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import AbstractSet, Callable, Final, Iterator, List, Optional, Protocol, Sequence

import pytest

import sampletones_application.logic.main.sources.scan as scan_module
import sampletones_core.reconstructions.converter.converter as converter_module
from sampletones_application.services.export.reporter import ExportProgressReporter
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_application.services.result import ServiceError, ServiceProgress
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.exports.stage import ExportStage
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.progress import STAGE_BEGUN, WHOLE_STAGE, ReconstructionReporter, announce
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.types.path import Pathlike
from tests.suite.conversion import COUNTED_STAGES, FAKE_FRAMES, HALFWAY

RELEASE_POLL_SECONDS: Final[float] = 0.05
HELD_ENTRY: Final[str] = "held-entry.txt"
FIRST_REPORT: Final[int] = 0


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


class RegenerationHold:
    """Holds every rebuild of an edited channel on its worker before it computes, until the scenario releases it.

    The rebuild waits where the real one runs, so the application draws and answers while the edit
    is on its way, and once released the real rebuild computes the edit's result. The hold lets
    every rebuild through from its release on, until the scenario holds again. A scenario standing
    for a rebuild that breaks lets the held rebuilds go as that failure instead, which the service
    reports the way it reports a rebuild that raised.
    """

    def __init__(self) -> None:
        self._released = threading.Event()
        self._lock = threading.Lock()
        self._waiting = 0
        self._failure: Optional[Exception] = None

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        rebuild = RegenerationService._run

        def held(
            service: RegenerationService,
            reconstruction: Reconstruction,
            channel_name: ChannelName,
            features: Features,
            heard: AbstractSet[int],
        ) -> None:
            self._wait()
            if self._failure is not None:
                service._emit(ServiceError(exception=self._failure))
                return

            rebuild(service, reconstruction, channel_name, features, heard)

        monkeypatch.setattr(RegenerationService, "_run", held)

    def waiting(self) -> int:
        """How many rebuilds stand held."""
        with self._lock:
            return self._waiting

    def release(self) -> None:
        self._released.set()

    def hold_again(self) -> None:
        """Holds every rebuild asked for from now on, as the hold did before its release."""
        self._released.clear()

    def fail(self, failure: Exception) -> None:
        """Lets every held rebuild, and every one asked for after, go as ``failure``."""
        self._failure = failure
        self._released.set()

    def _wait(self) -> None:
        with self._lock:
            self._waiting += 1

        self._released.wait()
        with self._lock:
            self._waiting -= 1


class ExportHold:
    """Holds every export at one report of its stages, until the scenario releases it.

    A run reports each stage it reaches and then asks whether it is still wanted. The hold answers
    that question at the report it stands at, once the export's window has heard the stage, so the
    window shows the run under way. While held, the run still hears a cancel and unwinds the way a
    cancel unwinds a real run. Released, every run goes on to its end until the scenario holds again.
    """

    def __init__(self) -> None:
        self._released = threading.Event()
        self._lock = threading.Lock()
        self._waiting = 0
        self._held_report = FIRST_REPORT

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        build = ExportProgressReporter.__init__

        def held(
            reporter: ExportProgressReporter,
            emit: Callable[[ServiceProgress[ExportStage]], None],
            withdrawn: Callable[[], bool],
        ) -> None:
            build(reporter, emit, self._gate(withdrawn))

        monkeypatch.setattr(ExportProgressReporter, "__init__", held)

    def waiting(self) -> int:
        """How many runs stand held."""
        with self._lock:
            return self._waiting

    def release(self) -> None:
        self._released.set()

    def hold_at(self, report: int) -> None:
        """Holds every run from now on at its report numbered ``report``, counted from 0, letting the earlier ones pass."""
        self._held_report = report
        self._released.clear()

    def _gate(self, withdrawn: Callable[[], bool]) -> Callable[[], bool]:
        """The question one run asks after each report, which waits at the held report until released or withdrawn."""
        reports = itertools.count()

        def asked() -> bool:
            if next(reports) == self._held_report:
                self._wait(withdrawn)

            return withdrawn()

        return asked

    def _wait(self, withdrawn: Callable[[], bool]) -> None:
        with self._lock:
            self._waiting += 1

        while not self._released.wait(RELEASE_POLL_SECONDS) and not withdrawn():
            continue

        with self._lock:
            self._waiting -= 1
