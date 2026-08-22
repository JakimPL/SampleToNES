from pathlib import Path
from typing import List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.converter.paths.utils import get_output_path, group_output_path
from sampletones_core.reconstructions.converter.plan.directory import DirectoryConversion
from sampletones_core.reconstructions.converter.plan.group import GroupConversion
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def stems(config: Config) -> StemsConfig:
    return StemsConfig.single_entry(list(config.generation.channels))


def _write_audio_files(directory: Path, names: List[str]) -> List[Path]:
    paths = []
    for name in names:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        paths.append(path)

    return paths


class TestGroupConversion:
    def test_one_source_makes_one_job_over_that_source(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        source = _write_audio_files(tmp_path, ["song.wav"])[0]

        jobs = GroupConversion(sources=(source,), stems=stems).jobs(config)

        assert len(jobs) == 1
        assert jobs[0].sources == (source,)
        assert jobs[0].stems == stems
        assert jobs[0].output_path == get_output_path(config, source)

    def test_several_sources_make_one_job_over_all_of_them(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        """Several recordings mix into one reconstruction, so they amount to one job."""
        sources = tuple(_write_audio_files(tmp_path, ["bass.wav", "drums.wav", "lead.wav"]))

        jobs = GroupConversion(sources=sources, stems=stems).jobs(config)

        assert len(jobs) == 1
        assert jobs[0].sources == sources
        assert jobs[0].output_path == group_output_path(config, sources)

    def test_the_setup_travels_with_the_job(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        sources = tuple(_write_audio_files(tmp_path, ["a.wav", "b.wav"]))
        targeted = StemsConfig.single_entry([ChannelName.PULSE1], channel_cap=1)

        jobs = GroupConversion(sources=sources, stems=targeted).jobs(config)

        assert jobs[0].stems == targeted


class TestDirectoryConversion:
    def test_every_audio_file_becomes_its_own_single_source_job(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        _write_audio_files(tmp_path, ["a.wav", "nested/b.wav"])

        jobs = DirectoryConversion(directory=tmp_path, stems=stems).jobs(config)

        assert len(jobs) == 2
        assert all(len(job.sources) == 1 for job in jobs)
        assert {job.sources[0].name for job in jobs} == {"a.wav", "b.wav"}

    def test_the_output_tree_mirrors_the_input_tree(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        _write_audio_files(tmp_path, ["nested/deeper/b.wav"])
        output_path = get_output_path(config, tmp_path)

        jobs = DirectoryConversion(directory=tmp_path, stems=stems).jobs(config)

        assert jobs[0].output_path == output_path / "nested" / "deeper" / "b.stn"

    def test_every_job_carries_the_same_setup(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        _write_audio_files(tmp_path, ["a.wav", "b.wav"])

        jobs = DirectoryConversion(directory=tmp_path, stems=stems).jobs(config)

        assert [job.stems for job in jobs] == [stems, stems]

    def test_a_directory_holding_nothing_to_convert_raises(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(NoFilesToProcessError):
            DirectoryConversion(directory=tmp_path, stems=stems).jobs(config)


def _config_writing_under(reconstructions_directory: Path) -> Config:
    """A configuration whose reconstructions are written under ``reconstructions_directory``."""
    config = Config()
    general = config.general.model_copy(update={"reconstructions_directory": str(reconstructions_directory)})
    return config.model_copy(update={"general": general})


class TestExistingTargets:
    """What a plan would write over, which is what a caller settles before starting a run."""

    def test_a_group_conversion_names_the_target_already_standing(
        self,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        config = _config_writing_under(tmp_path / "out")
        source = _write_audio_files(tmp_path, ["song.wav"])[0]
        plan = GroupConversion(sources=(source,), stems=stems)
        target = plan.jobs(config)[0].output_path
        target.parent.mkdir(parents=True)
        target.touch()

        assert plan.existing_targets(config) == (target,)

    def test_a_target_still_to_be_written_leaves_the_answer_empty(
        self,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        config = _config_writing_under(tmp_path / "out")
        source = _write_audio_files(tmp_path, ["song.wav"])[0]

        assert GroupConversion(sources=(source,), stems=stems).existing_targets(config) == ()

    def test_a_directory_sitting_at_the_target_path_leaves_the_answer_empty(
        self,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        """A target is a file, so a directory of that name is a different matter the run reports itself."""
        config = _config_writing_under(tmp_path / "out")
        source = _write_audio_files(tmp_path, ["song.wav"])[0]
        plan = GroupConversion(sources=(source,), stems=stems)
        plan.jobs(config)[0].output_path.mkdir(parents=True)

        assert plan.existing_targets(config) == ()

    def test_a_directory_conversion_settles_the_question_itself(
        self,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        """The scan converts what is still to be written, so a standing output puts nothing to the reader."""
        config = _config_writing_under(tmp_path / "out")
        _write_audio_files(tmp_path, ["a.wav"])
        plan = DirectoryConversion(directory=tmp_path, stems=stems)
        target = plan.jobs(config)[0].output_path
        target.parent.mkdir(parents=True)
        target.touch()

        assert plan.existing_targets(config) == ()


class TestGroupOutputPath:
    def test_one_source_names_the_file_after_itself(self, config: Config, tmp_path: Path) -> None:
        source = tmp_path / "song.wav"
        source.touch()
        assert group_output_path(config, (source,)) == get_output_path(config, source)

    def test_sources_sharing_a_directory_name_the_file_after_it(self, config: Config, tmp_path: Path) -> None:
        sources = tuple(_write_audio_files(tmp_path / "session", ["a.wav", "b.wav"]))
        assert group_output_path(config, sources).stem == "session"
