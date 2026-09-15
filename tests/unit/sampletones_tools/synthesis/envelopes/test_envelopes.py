from typing import Final

import numpy as np
import pytest
from pydantic import ValidationError

from sampletones_tools.synthesis.envelopes.exponential_decay import ExponentialDecayEnvelope
from sampletones_tools.synthesis.envelopes.gate import GateEnvelope
from sampletones_tools.synthesis.envelopes.linear_attack import LinearAttackEnvelope
from sampletones_tools.synthesis.envelopes.linear_ramp import LinearRampEnvelope
from sampletones_tools.synthesis.envelopes.periodic_decay import PeriodicDecayEnvelope

TIME_CONSTANT_SECONDS: Final[float] = 0.25
ATTACK_SECONDS: Final[float] = 0.005
GATE_START_SECONDS: Final[float] = 0.25
GATE_END_SECONDS: Final[float] = 0.5
STRIKE_PERIOD_SECONDS: Final[float] = 0.25
STRIKE_DELAY_SECONDS: Final[float] = 0.1
STRIKE_DECAY_SECONDS: Final[float] = 0.02


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


class TestGateEnvelope:
    def test_holds_full_level_inside_the_gate_and_silence_outside(self, time_axis: np.ndarray) -> None:
        envelope = GateEnvelope(kind="gate", start_seconds=GATE_START_SECONDS, end_seconds=GATE_END_SECONDS)
        values = envelope.render(time_axis)
        opening = int(np.searchsorted(time_axis, GATE_START_SECONDS))
        closing = int(np.searchsorted(time_axis, GATE_END_SECONDS))
        assert np.all(values[:opening] == 0.0)
        assert np.all(values[opening:closing] == 1.0)
        assert np.all(values[closing:] == 0.0)

    def test_a_gate_closing_before_it_opens_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            GateEnvelope(kind="gate", start_seconds=GATE_END_SECONDS, end_seconds=GATE_START_SECONDS)


class TestPeriodicDecayEnvelope:
    def test_is_silent_until_the_first_strike_and_full_on_every_strike(self, time_axis: np.ndarray) -> None:
        envelope = PeriodicDecayEnvelope(
            kind="periodic_decay",
            period_seconds=STRIKE_PERIOD_SECONDS,
            time_constant_seconds=STRIKE_DECAY_SECONDS,
            delay_seconds=STRIKE_DELAY_SECONDS,
        )
        values = envelope.render(time_axis)
        first_strike = int(np.searchsorted(time_axis, STRIKE_DELAY_SECONDS))
        second_strike = int(np.searchsorted(time_axis, STRIKE_DELAY_SECONDS + STRIKE_PERIOD_SECONDS))
        assert np.all(values[:first_strike] == 0.0)
        assert values[first_strike + 1] == pytest.approx(1.0, abs=1e-2)
        assert values[second_strike + 1] == pytest.approx(1.0, abs=1e-2)
        assert values[second_strike - 1] < np.exp(-STRIKE_PERIOD_SECONDS / STRIKE_DECAY_SECONDS / 2.0)
