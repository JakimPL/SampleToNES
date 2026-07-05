from typing import Final

import numpy as np
import pytest

from sampletones_synthesis.envelopes.exponential_decay import ExponentialDecayEnvelope
from sampletones_synthesis.envelopes.linear_attack import LinearAttackEnvelope
from sampletones_synthesis.envelopes.linear_ramp import LinearRampEnvelope

TIME_CONSTANT_SECONDS: Final[float] = 0.25
ATTACK_SECONDS: Final[float] = 0.005


class TestExponentialDecayEnvelope:
    def test_starts_at_full_level_and_reaches_inverse_e_at_the_time_constant(
        self,
        time_axis: np.ndarray,
        sample_rate: int,
    ) -> None:
        envelope = ExponentialDecayEnvelope(kind="exponential_decay", time_constant_seconds=TIME_CONSTANT_SECONDS)
        values = envelope.render(time_axis)
        constant_index = round(TIME_CONSTANT_SECONDS * sample_rate)
        assert values[0] == pytest.approx(1.0)
        assert values[constant_index] == pytest.approx(np.exp(-1.0), rel=1e-3)

    def test_decreases_monotonically(self, time_axis: np.ndarray) -> None:
        envelope = ExponentialDecayEnvelope(kind="exponential_decay", time_constant_seconds=TIME_CONSTANT_SECONDS)
        assert np.all(np.diff(envelope.render(time_axis)) < 0.0)


class TestLinearAttackEnvelope:
    def test_rises_linearly_then_holds_full_level(self, time_axis: np.ndarray, sample_rate: int) -> None:
        envelope = LinearAttackEnvelope(kind="linear_attack", attack_seconds=ATTACK_SECONDS)
        values = envelope.render(time_axis)
        hold_start = int(np.ceil(ATTACK_SECONDS * sample_rate))
        assert values[0] == pytest.approx(0.0)
        assert values[hold_start // 2] == pytest.approx(0.5, abs=0.01)
        assert np.all(values[hold_start:] == 1.0)


class TestLinearRampEnvelope:
    def test_rises_from_zero_to_one_over_the_axis(self, time_axis: np.ndarray) -> None:
        values = LinearRampEnvelope(kind="linear_ramp").render(time_axis)
        assert values[0] == pytest.approx(0.0)
        assert values[-1] == pytest.approx(1.0)
        assert np.all(np.diff(values) > 0.0)
