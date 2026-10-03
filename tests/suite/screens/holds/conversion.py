import time
from functools import partial
from pathlib import Path
from typing import AbstractSet, Sequence

import pytest

import sampletones_core.reconstructions.converter.converter as converter_module
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.progress import STAGE_BEGUN, WHOLE_STAGE, ReconstructionReporter, announce
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.types.path import Pathlike
from tests.suite.conversion import COUNTED_STAGES, FAKE_FRAMES, HALFWAY
from tests.suite.screens.holds.constants import RELEASE_POLL_SECONDS
from tests.suite.screens.holds.signal import ReleaseSignal


class HeldReconstructor:
    """A reconstructor that walks a run's stages, stops halfway through matching until released, and builds
    nothing.

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
        """Walks the stages of a reconstruction, holding halfway through matching, and answers with nothing
        built.

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
        """Replaces the converter's reconstructor with one that holds every run halfway through matching."""
        monkeypatch.setattr(
            converter_module,
            "Reconstructor",
            partial(HeldReconstructor, release_path=self._signal.path),
        )

    def release(self) -> None:
        """Lets every held run carry on to its end."""
        self._signal.release()
