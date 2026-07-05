from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_synthesis.oscillators.pulse import PulseOscillator

FREQUENCY: Final[float] = 220.0
DUTY_CYCLES: Final[Tuple[float, ...]] = (0.125, 0.25, 0.5)


class TestPulseOscillator:
    @pytest.mark.parametrize("duty_cycle", DUTY_CYCLES)
    def test_positive_fraction_matches_the_duty_cycle(
        self,
        duty_cycle: float,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        oscillator = PulseOscillator(kind="pulse", frequency=FREQUENCY, duty_cycle=duty_cycle)
        audio = oscillator.render(time_axis, generator=generator)
        assert np.mean(audio > 0.0) == pytest.approx(duty_cycle, abs=0.01)

    def test_values_alternate_between_full_levels(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        audio = PulseOscillator(kind="pulse", frequency=FREQUENCY, duty_cycle=0.5).render(
            time_axis,
            generator=generator,
        )
        assert set(np.unique(audio)) == {-1.0, 1.0}
