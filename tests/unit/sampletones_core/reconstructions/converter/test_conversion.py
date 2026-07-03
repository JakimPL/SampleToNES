from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_core.reconstructions.converter.conversion import reconstruct_file
from sampletones_core.reconstructions.reconstructor.reconstructor import Reconstructor
from sampletones_shared.exceptions import UnsupportedAudioFormatError


@pytest.fixture
def mock_reconstructor() -> MagicMock:
    return MagicMock(spec=Reconstructor)


class TestReconstructFile:
    def test_creates_parent_directory_when_not_exist(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "nested" / "dir" / "song.stn"
        reconstruct_file((mock_reconstructor, tmp_path / "song.wav", output_path))
        assert output_path.parent.exists()

    def test_saves_reconstruction_to_output_path(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstruction = MagicMock()
        mock_reconstructor.return_value = mock_reconstruction
        output_path = tmp_path / "song.stn"
        reconstruct_file((mock_reconstructor, tmp_path / "song.wav", output_path))
        mock_reconstruction.save.assert_called_once_with(output_path)

    def test_does_not_save_when_reconstructor_returns_none(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstructor.return_value = None
        output_path = tmp_path / "song.stn"
        result = reconstruct_file((mock_reconstructor, tmp_path / "song.wav", output_path))
        assert result == output_path

    def test_always_returns_output_path(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "song.stn"
        result = reconstruct_file((mock_reconstructor, tmp_path / "song.wav", output_path))
        assert result == output_path

    def test_unsupported_audio_format_error_is_swallowed(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstructor.side_effect = UnsupportedAudioFormatError("bad format")
        output_path = tmp_path / "song.stn"
        result = reconstruct_file((mock_reconstructor, tmp_path / "song.wav", output_path))
        assert result == output_path

    def test_keyboard_interrupt_is_reraised(
        self,
        mock_reconstructor: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_reconstructor.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            reconstruct_file(
                (mock_reconstructor, tmp_path / "song.wav", tmp_path / "song.stn"),
            )
