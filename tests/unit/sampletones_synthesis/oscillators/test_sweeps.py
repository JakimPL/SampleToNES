from dataclasses import dataclass
from typing import Callable, Final, Tuple

import numpy as np
import pytest
from scipy.integrate import cumulative_trapezoid

from sampletones_synthesis.oscillators.exponential_glide import ExponentialGlideOscillator
from sampletones_synthesis.oscillators.geometric_sweep import GeometricSweepOscillator
from sampletones_synthesis.oscillators.sine import SineOscillator
from sampletones_synthesis.protocols import Oscillator

FREQUENCY_START: Final[float] = 392.0
FREQUENCY_END: Final[float] = 44.0
TIME_CONSTANT_SECONDS: Final[float] = 0.25
PHASE_TOLERANCE_RADIANS: Final[float] = 1e-2

FrequencyProfile = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class SweepCase:
    name: str
    oscillator: Oscillator
    frequency_profile: FrequencyProfile


def _geometric_profile(time: np.ndarray) -> np.ndarray:
    ratio = FREQUENCY_END / FREQUENCY_START
    profile: np.ndarray = FREQUENCY_START * ratio ** (time / time[-1])
    return profile


def _glide_profile(time: np.ndarray) -> np.ndarray:
    profile: np.ndarray = FREQUENCY_END + (FREQUENCY_START - FREQUENCY_END) * np.exp(-time / TIME_CONSTANT_SECONDS)
    return profile


SWEEP_CASES: Final[Tuple[SweepCase, ...]] = (
    SweepCase(
        name="geometric",
        oscillator=GeometricSweepOscillator(
            kind="geometric_sweep",
            frequency_start=FREQUENCY_START,
            frequency_end=FREQUENCY_END,
        ),
        frequency_profile=_geometric_profile,
    ),
    SweepCase(
        name="exponential_glide",
        oscillator=ExponentialGlideOscillator(
            kind="exponential_glide",
            frequency_start=FREQUENCY_START,
            frequency_end=FREQUENCY_END,
            time_constant_seconds=TIME_CONSTANT_SECONDS,
        ),
        frequency_profile=_glide_profile,
    ),
)


class TestSweepOscillators:
    @pytest.mark.parametrize("case", SWEEP_CASES, ids=lambda case: case.name)
    def test_closed_form_matches_numerical_phase_integration(
        self,
        case: SweepCase,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        """
        The rendered waveform equals the sine of the numerically integrated
        frequency profile, confirming the closed-form phase formulas.
        """
        audio = case.oscillator.render(time_axis, generator=generator)
        numerical_phase = (
            2.0
            * np.pi
            * cumulative_trapezoid(
                case.frequency_profile(time_axis),
                time_axis,
                initial=0.0,
            )
        )
        assert np.allclose(
            audio,
            np.sin(numerical_phase),
            atol=PHASE_TOLERANCE_RADIANS,
        )

    def test_equal_endpoints_render_a_steady_tone(
        self,
        time_axis: np.ndarray,
        generator: np.random.Generator,
    ) -> None:
        sweep = GeometricSweepOscillator(
            kind="geometric_sweep",
            frequency_start=FREQUENCY_START,
            frequency_end=FREQUENCY_START,
        )
        tone = SineOscillator(kind="sine", frequency=FREQUENCY_START)
        assert np.array_equal(
            sweep.render(time_axis, generator=generator),
            tone.render(time_axis, generator=generator),
        )
