from typing import Final

import numpy as np
import pytest

from sampletones_synthesis.envelopes.exponential_decay import ExponentialDecayEnvelope
from sampletones_synthesis.envelopes.linear_attack import LinearAttackEnvelope
from sampletones_synthesis.oscillators.sine import SineOscillator
from sampletones_synthesis.voice.layer import Layer

FREQUENCY: Final[float] = 220.0
TIME_CONSTANT_SECONDS: Final[float] = 0.3
ATTACK_SECONDS: Final[float] = 0.005


class TestLayer:
    def test_gain_scales_the_waveform(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        oscillator = SineOscillator(kind="sine", frequency=FREQUENCY)
        unit = Layer(oscillator=oscillator, envelopes=(), gain=1.0).render(
            time_axis,
            generator=generator,
        )
        halved = Layer(oscillator=oscillator, envelopes=(), gain=0.5).render(
            time_axis,
            generator=generator,
        )
        assert np.allclose(halved, 0.5 * unit)

    def test_envelopes_stack_multiplicatively(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        attack = LinearAttackEnvelope(
            kind="linear_attack",
            attack_seconds=ATTACK_SECONDS,
        )
        decay = ExponentialDecayEnvelope(
            kind="exponential_decay",
            time_constant_seconds=TIME_CONSTANT_SECONDS,
        )
        layer = Layer(
            oscillator=SineOscillator(kind="sine", frequency=FREQUENCY),
            envelopes=(attack, decay),
            gain=1.0,
        )
        expected = (
            SineOscillator(kind="sine", frequency=FREQUENCY).render(
                time_axis,
                generator=generator,
            )
            * attack.render(time_axis)
            * decay.render(time_axis)
        )
        assert np.allclose(
            layer.render(time_axis, generator=generator),
            expected,
        )

    def test_nonpositive_gain_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            Layer(
                oscillator=SineOscillator(kind="sine", frequency=FREQUENCY),
                envelopes=(),
                gain=0.0,
            )
