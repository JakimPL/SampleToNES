from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.conversion import reconstruct_job
from sampletones_core.reconstructions.converter.job import ConversionJob
from sampletones_core.reconstructions.reconstructor.reconstructor import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import UnsupportedAudioFormatError


@pytest.fixture
def mock_reconstructor() -> MagicMock:
    return MagicMock(spec=Reconstructor)


def _job(tmp_path: Path, output_path: Path) -> ConversionJob:
    return ConversionJob(
        sources=(tmp_path / "song.wav",),
        stems=StemsConfig.single_entry(list(Config().generation.channels)),
        output_path=output_path,
    )


class TestReconstructJob:
    def test_creates_parent_directory_when_not_exist(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "nested" / "dir" / "song.stn"
        reconstruct_job((mock_reconstructor, _job(tmp_path, output_path)))
        assert output_path.parent.exists()

    def test_builds_the_reconstruction_from_the_jobs_sources_and_setup(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        job = _job(tmp_path, tmp_path / "song.stn")
        reconstruct_job((mock_reconstructor, job))
        mock_reconstructor.reconstruct.assert_called_once_with(job.sources, job.stems)

    def test_saves_reconstruction_to_output_path(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction = MagicMock()
        mock_reconstructor.reconstruct.return_value = mock_reconstruction
        output_path = tmp_path / "song.stn"
        reconstruct_job((mock_reconstructor, _job(tmp_path, output_path)))
        mock_reconstruction.save.assert_called_once_with(output_path)

    def test_reports_the_output_path_when_the_reconstruction_is_empty(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstructor.reconstruct.return_value = None
        output_path = tmp_path / "song.stn"
        assert reconstruct_job((mock_reconstructor, _job(tmp_path, output_path))) == output_path

    def test_always_returns_output_path(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "song.stn"
        assert reconstruct_job((mock_reconstructor, _job(tmp_path, output_path))) == output_path

    def test_unsupported_audio_format_error_is_swallowed(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstructor.reconstruct.side_effect = UnsupportedAudioFormatError("bad format")
        output_path = tmp_path / "song.stn"
        assert reconstruct_job((mock_reconstructor, _job(tmp_path, output_path))) == output_path

    def test_keyboard_interrupt_is_reraised(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstructor.reconstruct.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            reconstruct_job((mock_reconstructor, _job(tmp_path, tmp_path / "song.stn")))
