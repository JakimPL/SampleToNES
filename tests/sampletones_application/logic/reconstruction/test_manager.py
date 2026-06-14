from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_shared.exceptions import LoadReconstructionError


class TestLoadReconstructionPropagatesErrors:
    @staticmethod
    def _manager() -> ReconstructionManager:
        return ReconstructionManager(scheduling=MagicMock())

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            self._manager().load_reconstruction(tmp_path / "nope.stn")

    def test_directory_raises_is_a_directory(self, tmp_path: Path) -> None:
        with pytest.raises(IsADirectoryError):
            self._manager().load_reconstruction(tmp_path)

    def test_foreign_file_raises_load_reconstruction_error(self, tmp_path: Path) -> None:
        foreign = tmp_path / "kick.wav"
        foreign.write_bytes(b"RIFF\x58\xb9\x00\x00WAVEfmt " + b"\x00" * 256)

        with pytest.raises(LoadReconstructionError):
            self._manager().load_reconstruction(foreign)
