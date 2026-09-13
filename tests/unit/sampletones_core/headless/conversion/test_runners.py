from pathlib import Path
from typing import List, Tuple

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.headless.conversion import runners
from sampletones_core.headless.conversion.request import ConversionRequest, classic_setup
from sampletones_core.headless.conversion.runners import reconstruct
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from tests.unit.sampletones_core.headless.conversion.stems import recording


class TestReconstruct:
    def test_recordings_are_mixed_into_one_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        calls: List[Tuple[Tuple[Path, ...], Path]] = []

        def reconstruct_sources(
            sources: Tuple[Path, ...], config: Config, stems: StemsConfig, output_path: Path
        ) -> None:
            del config, stems
            calls.append((sources, output_path))

        monkeypatch.setattr(runners, "reconstruct_sources", reconstruct_sources)
        source = recording(tmp_path, "song.wav")
        request = ConversionRequest(
            sources=(source,), stems=classic_setup(DEFAULT_CHANNELS), output_path=tmp_path / "x.stn"
        )

        reconstruct(request, Config())

        assert calls == [((source,), tmp_path / "x.stn")]

    def test_a_directory_is_walked(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        walked: List[Path] = []

        def reconstruct_directory(directory: Path, config: Config, stems: StemsConfig) -> None:
            del config, stems
            walked.append(directory)

        monkeypatch.setattr(runners, "reconstruct_directory", reconstruct_directory)
        request = ConversionRequest(sources=(tmp_path,), stems=classic_setup(DEFAULT_CHANNELS), output_path=None)

        reconstruct(request, Config())

        assert walked == [tmp_path]
