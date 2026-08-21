from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from sampletones_application.services.conversion import ConversionService
from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter import DirectoryConversion, GroupConversion
from sampletones_core.reconstructions.converter.plan.protocol import ConversionPlan
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig


def _stems(config: Config) -> StemsConfig:
    return StemsConfig.single_entry(list(config.generation.channels))


class TestConversionServiceArgumentRouting:
    """The service hands the converter the configuration and the plan it was given, untouched.

    What a request converts is decided above the service, so the service's whole part is to
    build a converter around that decision and drive its callbacks. The converter itself stays
    patched here: running one needs real audio and a process pool.
    """

    def _start_with_captured_kwargs(self, config: Config, plan: ConversionPlan) -> Dict[str, Any]:
        with patch("sampletones_application.services.conversion.ReconstructionConverter") as mock_class:
            mock_class.return_value = MagicMock()
            ConversionService().start(config, plan)

        return dict(mock_class.call_args.kwargs)

    def test_start_passes_config_to_converter(self, tmp_path: Path, default_config: Config) -> None:
        real_file = tmp_path / "sample.wav"
        real_file.write_bytes(b"")
        plan = GroupConversion(sources=(real_file,), stems=_stems(default_config))

        assert self._start_with_captured_kwargs(default_config, plan)["config"] is default_config

    def test_start_passes_the_plan_to_converter(self, tmp_path: Path, default_config: Config) -> None:
        real_file = tmp_path / "sample.wav"
        real_file.write_bytes(b"")
        plan = GroupConversion(sources=(real_file,), stems=_stems(default_config))

        assert self._start_with_captured_kwargs(default_config, plan)["plan"] is plan

    def test_a_directory_plan_reaches_the_converter_as_it_is(self, tmp_path: Path, default_config: Config) -> None:
        real_directory = tmp_path / "samples"
        real_directory.mkdir()
        plan = DirectoryConversion(directory=real_directory, stems=_stems(default_config))

        assert self._start_with_captured_kwargs(default_config, plan)["plan"] is plan


class TestDirectoryPlanReadsTheFilesystem:
    """A directory plan resolves against the real tree, which is where a batch's jobs come from."""

    def test_every_audio_file_below_the_directory_becomes_a_job(
        self,
        tmp_path: Path,
        default_config: Config,
    ) -> None:
        (tmp_path / "nested").mkdir()
        (tmp_path / "a.wav").write_bytes(b"")
        (tmp_path / "nested" / "b.wav").write_bytes(b"")
        (tmp_path / "notes.txt").write_text("not audio")

        jobs = DirectoryConversion(directory=tmp_path, stems=_stems(default_config)).jobs(default_config)

        assert {job.sources[0].name for job in jobs} == {"a.wav", "b.wav"}
        assert all(job.output_path.suffix == ".stn" for job in jobs)
