from pathlib import Path
from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, MIN_SAMPLE_RATE, SAMPLE_RATES
from sampletones_core.constants.enums import DEFAULT_CHANNELS
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.corpus.catalog import build_mini_library

OFF_LIST_RATE: Final[int] = 11025
LIBRARY_RATES: Final[Tuple[int, ...]] = (MIN_SAMPLE_RATE, OFF_LIST_RATE)
TONE_FREQUENCY: Final[float] = 330.0
TONE_AMPLITUDE: Final[float] = 0.5
DURATION_SECONDS: Final[float] = 0.25


def _write_tone(path: Path, sample_rate: int) -> Path:
    time = np.arange(int(sample_rate * DURATION_SECONDS)) / sample_rate
    write_wave(path, sample_rate, TONE_AMPLITUDE * np.sin(2 * np.pi * TONE_FREQUENCY * time))
    return path


class TestALibraryBuiltAtAnAcceptedRateConverts:
    """A library built at any rate the settings accept, the offered list's lowest bound and a rate
    missing from that list alike, converts a recording written at its own rate or at another one."""

    @pytest.mark.parametrize("library_rate", LIBRARY_RATES)
    @pytest.mark.parametrize("recording_rate", (OFF_LIST_RATE, DEFAULT_SAMPLE_RATE))
    def test_the_conversion_spans_the_recording(self, tmp_path: Path, library_rate: int, recording_rate: int) -> None:
        assert OFF_LIST_RATE not in SAMPLE_RATES
        config = Config().with_library(sample_rate=library_rate)
        reconstructor = Reconstructor(config, frozenset(DEFAULT_CHANNELS), library=build_mini_library(config))
        recording = _write_tone(tmp_path / "tone.wav", recording_rate)

        reconstruction = reconstructor.reconstruct(
            [recording],
            StemsConfig.single_entry(StemSettings.covering(list(DEFAULT_CHANNELS))),
        )

        assert reconstruction is not None
        expected_frames = int(library_rate * DURATION_SECONDS) // config.library.frame_length
        lengths = [len(instructions) for instructions in reconstruction.instructions.values() if instructions]
        assert lengths
        assert all(abs(length - expected_frames) <= 1 for length in lengths)
