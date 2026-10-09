from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.fft.window.cyclic import CyclicArray
from tests.suite.analysis import analyzed_config

SAMPLE_LENGTH: Final[int] = 500
SHIFTS: Final[Tuple[int, ...]] = (0, 137, SAMPLE_LENGTH - 1)
TAPER_EXTENSIONS: Final[Tuple[int, ...]] = (0, 1)
SEED: Final[int] = 7


class TestAFrameIsTheMiddleOfItsWindow:
    """A sample's frame is the middle of the windowed fragment the same shift reads, under the envelope
    there: for the flat constant-Q envelope, the FFT's tapered one, and a taper an odd number of samples
    long, whose frame reaches one tapered sample. The sample is shorter than a frame, so the reading
    wraps around it."""

    @pytest.mark.parametrize("shift", SHIFTS)
    @pytest.mark.parametrize("extension", TAPER_EXTENSIONS)
    @pytest.mark.parametrize("method", (SpectrumMethod.CQT, SpectrumMethod.FFT))
    def test_the_frame_equals_the_middle_of_the_windowed_fragment(
        self,
        method: SpectrumMethod,
        extension: int,
        shift: int,
    ) -> None:
        config = analyzed_config(method, gamma=0)
        window = Window.from_config(config, custom_size=Window.from_config(config).size + extension)
        audio = np.random.default_rng(SEED).standard_normal(SAMPLE_LENGTH).astype(np.float32)
        sample = CyclicArray(array=audio, sample_rate=config.library.sample_rate)

        expected = window.get_frame_from_window(sample.get_windowed_fragment(shift, window))

        np.testing.assert_array_equal(sample.get_frame(shift, window), expected)
