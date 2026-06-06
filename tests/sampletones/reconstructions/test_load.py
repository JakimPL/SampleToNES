from pathlib import Path

import pytest

from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import LoadReconstructionError


class TestLoadRejectsForeignFiles:
    def test_non_reconstruction_file_raises_load_error(self, tmp_path: Path) -> None:
        foreign = tmp_path / "kick.wav"
        foreign.write_bytes(b"RIFF\x58\xb9\x00\x00WAVEfmt " + b"\x00" * 256)

        with pytest.raises(LoadReconstructionError):
            Reconstruction.load(foreign)
