from pathlib import Path
from typing import Final, FrozenSet, Sequence

from sampletones_core.configs import Config
from sampletones_core.reconstructions.progress import (
    STAGE_BEGUN,
    WHOLE_STAGE,
    ReconstructionReporter,
    announce,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.types.path import Pathlike
from tests.suite.release import wait_for_release

FAKE_FRAMES: Final[int] = 40
HALFWAY: Final[int] = FAKE_FRAMES // 2
COUNTED_STAGES: Final[FrozenSet[ReconstructionStage]] = frozenset(
    {ReconstructionStage.MATCHING, ReconstructionStage.RENDERING}
)


class FakeReconstructor:
    """A reconstructor that walks the stages a real one does and builds nothing.

    Reconstructing needs an instruction library and seconds of arithmetic per frame, none of which
    the wiring under test depends on: what a run hands its jobs, what those jobs report, and how
    the run reads it back. Walking the stages stands in for the work, and the run is left with no
    file to write, which is what a job whose reconstruction came to nothing already does.

    Travels to a worker with the job, the way the real one does, so it is a plain picklable object
    built from a configuration the same way — which is what lets a run construct one in its place.
    The walk pauses halfway through matching until the test releases it, so an assertion about a
    reconstruction under way is made while that reconstruction is provably under way.
    """

    def __init__(self, config: Config, release_path: Path, *, frames: int = FAKE_FRAMES) -> None:
        self.config = config
        self.release_path = release_path
        self.frames = frames

    def reconstruct(
        self,
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
        *,
        report: ReconstructionReporter,
    ) -> None:
        """Walks the stages of a reconstruction, reporting each, and answers with nothing built.

        The walk follows the stages in the order they are declared, so it passes through them the
        way a reconstruction does however that order comes to change.

        Raises:
            OperationCancelled: If the walk is withdrawn while it is under way.
        """
        for stage in ReconstructionStage:
            if stage not in COUNTED_STAGES:
                announce(report, stage, STAGE_BEGUN, WHOLE_STAGE)
                continue

            self._walk(report, stage)

    def _walk(self, report: ReconstructionReporter, stage: ReconstructionStage) -> None:
        for frame in range(self.frames + 1):
            announce(report, stage, frame, self.frames)
            if stage == ReconstructionStage.MATCHING and frame == HALFWAY:
                wait_for_release(self.release_path)


def write_silent_recording(path: Path) -> Path:
    """Leaves a file where a recording would be, since the walk above reads none."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path
