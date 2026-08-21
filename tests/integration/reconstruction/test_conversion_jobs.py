from pathlib import Path

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.converter import (
    DirectoryConversion,
    GroupConversion,
    reconstruct_job,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from tests.integration.assets.reconstruction import (
    build_mini_library,
    three_stem_config,
    three_stem_reconstruction_config,
    write_three_stem_recordings,
)


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
        written = reconstruct_job((reconstructor, jobs[0]))

        assert written.exists()
        loaded = Reconstruction.load(written)
        assert loaded.audio_filepath == sources
        assert loaded.stems_data.config == three_stem_config()
        assert set(loaded.stems_data.assignments_by_channel) == set(loaded.playing_channels)

    def test_one_source_converts_the_classic_way(self, tmp_path: Path) -> None:
        config = _writing_to(Config(), tmp_path / "out")
        reconstructor = Reconstructor(config, library=build_mini_library(config))
        source = write_three_stem_recordings(config, tmp_path)[0]
        stems = StemsConfig.single_entry(list(config.generation.channels))

        jobs = GroupConversion(sources=(source,), stems=stems).jobs(config)
        written = reconstruct_job((reconstructor, jobs[0]))

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
        stems = StemsConfig.single_entry([ChannelName.PULSE1], channel_cap=1)

        jobs = DirectoryConversion(directory=recordings, stems=stems).jobs(config)

        assert len(jobs) == len(sources)
        for job in jobs:
            written = reconstruct_job((reconstructor, job))
            loaded = Reconstruction.load(written)
            assert loaded.audio_filepath == job.sources
            assert tuple(loaded.playing_channels) == (ChannelName.PULSE1,)
