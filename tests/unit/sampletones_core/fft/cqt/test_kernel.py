from typing import Final

import numpy as np
import pytest

from sampletones_core.constants.enums import CQTWindow
from sampletones_core.fft.cqt.kernel import window_envelope
from tests.suite.base import BaseTestSuite

LENGTH: Final[int] = 64


class TestWindowEnvelope(BaseTestSuite):
    """The envelope each constant-Q wavelet is weighed by, which the reconstructor's window model reads too."""

    def test_the_rectangular_envelope_weighs_every_sample_alike(self) -> None:
        assert np.array_equal(window_envelope(CQTWindow.RECTANGULAR, LENGTH), np.ones(LENGTH))

    def test_consecutive_hann_envelopes_tile_without_a_seam(self) -> None:
        """Half a length apart, the periodic Hann envelopes sum to one at every sample."""
        envelope = window_envelope(CQTWindow.HANN, LENGTH)
        half = LENGTH // 2

        assert envelope[:half] + envelope[half:] == pytest.approx(np.ones(half))
        assert envelope[0] == pytest.approx(0.0)
