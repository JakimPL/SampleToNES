from __future__ import annotations

from typing import Final

import numpy as np
import pytest

from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.mix import FrameMix

VARIANCE: Final[float] = 0.25


def _contribution(fragment: Fragment, scale: float) -> Contribution:
    bins = len(fragment.feature.values)
    frame_length = fragment.audio.shape[0]
    return Contribution(
        power=np.full(bins, scale),
        expectation=np.full(frame_length, scale),
        variance=scale * VARIANCE,
    )


class TestFrameMix:
    def test_an_empty_mix_sounds_nothing(self, synthetic_fragment: Fragment) -> None:
        mix = FrameMix.empty(synthetic_fragment)

        assert mix.power.shape == (len(synthetic_fragment.feature.values),)
        assert mix.expectation.shape == synthetic_fragment.audio.shape
        assert not np.any(mix.power) and not np.any(mix.expectation)
        assert mix.variance == 0.0

    def test_contributions_add_their_power_waveform_and_variance(self, synthetic_fragment: Fragment) -> None:
        first = _contribution(synthetic_fragment, 1.0)
        second = _contribution(synthetic_fragment, 2.0)

        mix = FrameMix.of(synthetic_fragment, [first, second])

        np.testing.assert_allclose(mix.power, first.power + second.power)
        np.testing.assert_allclose(mix.expectation, first.expectation + second.expectation)
        assert mix.variance == pytest.approx(3.0 * VARIANCE)

    def test_the_residual_waveform_is_what_the_mix_leaves_of_the_frame(self, synthetic_fragment: Fragment) -> None:
        contribution = _contribution(synthetic_fragment, 0.5)

        residual = FrameMix.empty(synthetic_fragment).added(contribution).residual_waveform(synthetic_fragment)

        np.testing.assert_allclose(residual, np.asarray(synthetic_fragment.audio, dtype=np.float64) - 0.5)
