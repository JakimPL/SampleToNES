from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Final, Iterator, Tuple
from unittest.mock import patch

import pytest

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter import GroupConversion, ReconstructionConverter
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.stage import ReconstructionStage
from tests.suite.conversion import FakeReconstructor, write_silent_recording
from tests.suite.parallelization import ProgressRecorder, stands_partway

RECONSTRUCTOR_PATCH: Final[str] = "sampletones_core.reconstructions.converter.converter.Reconstructor"
READING_TIMEOUT: Final[float] = 60.0
POOL_TIMEOUT: Final[float] = 120.0
LONE_WORKER: Final[int] = 1
ONE_JOB: Final[int] = 1
WHOLE_RUN: Final[float] = 1.0
RELEASE_NAME: Final[str] = "release"


def _config(tmp_path: Path) -> Config:
    """A configuration writing under the test's own directory, with one worker to run in."""
    general = Config().general.model_copy(
        update={"reconstructions_directory": str(tmp_path / "out"), "max_workers": LONE_WORKER}
    )
    return Config().model_copy(update={"general": general})


@contextmanager
def conversion_run(tmp_path: Path) -> Iterator[Tuple[ReconstructionConverter, ProgressRecorder, Path]]:
    """Runs one conversion through the pool with the reconstruction itself standing in.

    The release file is written on the way out whatever the test did, so a run whose assertion
    failed before releasing its job still ends rather than holding a worker at its halfway mark.
    """
    config = _config(tmp_path)
    source = write_silent_recording(tmp_path / "kick.wav")
    release_path = tmp_path / RELEASE_NAME
    stems = StemsConfig.single_entry(list(config.generation.channels))
    plan = GroupConversion(sources=(source,), stems=stems)

    recorder = ProgressRecorder()
    converter = ReconstructionConverter(config=config, plan=plan)
    converter.set_callbacks(on_progress=recorder)
    standing_in = partial(FakeReconstructor, release_path=release_path)
    with patch(RECONSTRUCTOR_PATCH, standing_in):
        converter.start()
        try:
            yield converter, recorder, release_path
        finally:
            release_path.touch(exist_ok=True)
            converter.shutdown()


class TestASingleConversionReportsItself:
    """One recording is one job, and the run says how far that job has come while it runs.

    This is the whole path the reader watches: the run hands the job a line, the job walks its
    stages over it from a worker process, and the run reads the stages back as one climbing
    figure. The reconstruction itself stands in, since what is under test is the wiring.
    """

    def test_the_run_stands_between_its_ends_while_its_one_job_runs(self, tmp_path: Path) -> None:
        with conversion_run(tmp_path) as (converter, recorder, release_path):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)

            release_path.touch()
            converter.wait(POOL_TIMEOUT)

    def test_the_run_names_the_recording_it_is_reading(self, tmp_path: Path) -> None:
        with conversion_run(tmp_path) as (converter, recorder, release_path):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)
            release_path.touch()
            converter.wait(POOL_TIMEOUT)

            named = {progress.current_item for _, progress in recorder.readings if progress.current_item}

            assert named == {str(tmp_path / "kick.wav")}

    def test_the_stages_reach_the_run_as_the_job_named_them(self, tmp_path: Path) -> None:
        """A reading is where the job stands, so a stage passed through in one step may be read
        together with the one after it; what every reading carries is a stage the job named."""
        with conversion_run(tmp_path) as (converter, recorder, release_path):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)
            release_path.touch()
            converter.wait(POOL_TIMEOUT)

            stages = {step.stage for step in recorder.steps}

            assert stages <= {stage.value for stage in ReconstructionStage}
            assert ReconstructionStage.MATCHING.value in stages

    def test_the_run_climbs_to_its_end(self, tmp_path: Path) -> None:
        with conversion_run(tmp_path) as (converter, recorder, release_path):
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)
            release_path.touch()
            converter.wait(POOL_TIMEOUT)

            fractions = recorder.fractions
            assert fractions == sorted(fractions)
            assert max(fractions) == pytest.approx(WHOLE_RUN)
