from pathlib import Path

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, bending_channels
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.converter import (
    DirectoryConversion,
    GroupConversion,
    reconstruct_job,
)
from sampletones_core.reconstructions.progress import (
    ReconstructionProgress,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.exceptions import OperationCanceled
from sampletones_shared.utils.progress import silent_reporter
from tests.integration.assets.reconstruction import (
    build_mini_library,
    three_stem_config,
    three_stem_reconstruction_config,
    write_three_stem_recordings,
)
from tests.suite.progress import FIRST_REPORT, RecordingReporter, reported_stages


def _writing_to(config: Config, directory: Path) -> Config:
    general = config.general.model_copy(update={"reconstructions_directory": str(directory)})
    return config.model_copy(update={"general": general})


class TestGroupConversionEndToEnd:
    """Several recordings reach one written reconstruction through the job seam."""

    def test_three_stems_convert_into_one_reconstruction_file(self, tmp_path: Path) -> None:
        config = _writing_to(three_stem_reconstruction_config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        sources = write_three_stem_recordings(config, tmp_path)

        jobs = GroupConversion(sources=sources, stems=three_stem_config()).jobs(config)

        assert len(jobs) == 1
        written = reconstruct_job((reconstructor, jobs[0], silent_reporter))

        assert written.exists()
        loaded = Reconstruction.load(written)
        assert loaded.audio_filepath == sources
        assert loaded.stems_data.config == three_stem_config()
        assert set(loaded.stems_data.assignments_by_channel) == set(loaded.playing_channels)

    def test_one_source_converts_the_classic_way(self, tmp_path: Path) -> None:
        config = _writing_to(Config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        source = write_three_stem_recordings(config, tmp_path)[0]
        channels = list(config.generation.channels)
        stems = StemsConfig.single_entry(channels, bending_channels(channels))

        jobs = GroupConversion(sources=(source,), stems=stems).jobs(config)
        written = reconstruct_job((reconstructor, jobs[0], silent_reporter))

        loaded = Reconstruction.load(written)
        assert written.stem == source.stem
        assert loaded.audio_filepath == (source,)
        assert loaded.stems_data.config == stems


class TestDirectoryConversionEndToEnd:
    """A directory converts into one reconstruction per audio file, each from that file alone."""

    def test_each_recording_is_written_on_its_own(self, tmp_path: Path) -> None:
        config = _writing_to(Config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        recordings = tmp_path / "recordings"
        recordings.mkdir()
        sources = write_three_stem_recordings(config, recordings)
        stems = StemsConfig.single_entry([ChannelName.PULSE1], bending_channels([ChannelName.PULSE1]), channel_cap=1)

        jobs = DirectoryConversion(directory=recordings, stems=stems).jobs(config)

        assert len(jobs) == len(sources)
        for job in jobs:
            written = reconstruct_job((reconstructor, job, silent_reporter))
            loaded = Reconstruction.load(written)
            assert loaded.audio_filepath == job.sources
            assert tuple(loaded.playing_channels) == (ChannelName.PULSE1,)


class TestAJobReportsItselfAsItRuns:
    """A job says which stage it is in and how far that stage has come, over the real pipeline.

    A conversion is one job whatever the number of stems, so without this a whole reconstruction
    stands at nothing until the file is written. The run reported here is the real one over a
    small library, so what the stages count is what the reconstruction actually did.
    """

    def test_the_run_passes_through_its_stages_in_order(self, tmp_path: Path) -> None:
        config = _writing_to(three_stem_reconstruction_config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        sources = write_three_stem_recordings(config, tmp_path)
        jobs = GroupConversion(sources=sources, stems=three_stem_config()).jobs(config)
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter()

        reconstruct_job((reconstructor, jobs[0], reporter))

        assert reported_stages(reporter.reports) == list(ReconstructionStage)

    def test_the_reading_climbs_from_nothing_to_the_whole_run(self, tmp_path: Path) -> None:
        config = _writing_to(Config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        source = write_three_stem_recordings(config, tmp_path)[0]
        channels = list(config.generation.channels)
        stems = StemsConfig.single_entry(channels, bending_channels(channels))
        jobs = GroupConversion(sources=(source,), stems=stems).jobs(config)
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter()

        reconstruct_job((reconstructor, jobs[0], reporter))
        readings = [report.fraction for report in reporter.reports]

        assert readings == sorted(readings)
        assert readings[0] == 0.0
        assert readings[-1] == 1.0

    def test_the_matching_stage_counts_the_frames_the_recording_holds(self, tmp_path: Path) -> None:
        config = _writing_to(Config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        source = write_three_stem_recordings(config, tmp_path)[0]
        channels = list(config.generation.channels)
        stems = StemsConfig.single_entry(channels, bending_channels(channels))
        jobs = GroupConversion(sources=(source,), stems=stems).jobs(config)
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter()

        reconstruct_job((reconstructor, jobs[0], reporter))
        matching = [report for report in reporter.reports if report.stage == ReconstructionStage.MATCHING]

        assert [report.completed for report in matching] == list(range(matching[0].total + 1))

    def test_a_withdrawn_job_unwinds_and_writes_nothing(self, tmp_path: Path) -> None:
        config = _writing_to(Config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        source = write_three_stem_recordings(config, tmp_path)[0]
        channels = list(config.generation.channels)
        stems = StemsConfig.single_entry(channels, bending_channels(channels))
        jobs = GroupConversion(sources=(source,), stems=stems).jobs(config)
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)

        with pytest.raises(OperationCanceled):
            reconstruct_job((reconstructor, jobs[0], reporter))

        assert not jobs[0].output_path.exists()
