from dataclasses import dataclass
from typing import Tuple

import numpy as np

from sampletones_core.constants.general import (
    APU_CLOCK,
    MAX_LFSR,
    MAX_LFSR_SHORT,
    NOISE_PERIODS,
)


@dataclass(frozen=True)
class NoiseReferenceState:
    """The 2A03 noise channel's resumable state: the shift register and the clock phase.

    ``clock`` is the fractional position within the current shift-register step, in the
    range ``[0.0, 1.0)``, so a render continues exactly where the previous one ended.
    """

    lfsr: int
    clock: float


def step_lfsr(lfsr: int, short: bool) -> int:
    """Advances the 15-bit noise shift register by one step.

    Feedback is ``bit0 ^ bit1`` in long mode and ``bit0 ^ bit6`` in short mode, shifted
    into bit 14, matching the 2A03 hardware.

    Args:
        lfsr: The current shift-register value, 1 to ``MAX_LFSR``.
        short: Whether the register runs in its 93-step short mode.

    Returns:
        int: The shift register after one step.
    """
    feedback = (lfsr & 1) ^ ((lfsr >> (6 if short else 1)) & 1)
    return ((lfsr >> 1) | (feedback << 14)) & MAX_LFSR


def lfsr_cycle_length(short: bool) -> int:
    """The number of steps after which the shift register repeats."""
    return MAX_LFSR_SHORT if short else MAX_LFSR


def shift_rate(period_index: int) -> float:
    """The shift register's clock rate in Hz for a noise period index.

    The noise timer is clocked at the CPU rate and reloads with the period, so the
    register advances ``APU_CLOCK / period`` times per second.

    Args:
        period_index: Index into ``NOISE_PERIODS``, 0 (slowest) to 15 (fastest).

    Returns:
        float: The shift rate in Hz.
    """
    return APU_CLOCK / float(NOISE_PERIODS[period_index])


def tone_frequency(period_index: int, short: bool) -> float:
    """The rate in Hz at which the whole noise sequence repeats.

    Args:
        period_index: Index into ``NOISE_PERIODS``.
        short: Whether the register runs in its 93-step short mode.

    Returns:
        float: The repetition frequency of the noise pattern.
    """
    return shift_rate(period_index) / float(lfsr_cycle_length(short))


def bit_density(short: bool) -> float:
    """The fraction of a full shift-register cycle in which the output bit is set.

    Long mode is balanced; short mode is strongly asymmetric, and that asymmetry is what
    gives it its metallic character.

    Args:
        short: Whether the register runs in its 93-step short mode.

    Returns:
        float: The density of set output bits over one cycle.
    """
    lfsr = 1
    ones = 0
    for _ in range(lfsr_cycle_length(short)):
        ones += lfsr & 1
        lfsr = step_lfsr(lfsr, short)

    return ones / float(lfsr_cycle_length(short))


def reference_noise_frame(
    *,
    period_index: int,
    short: bool,
    sample_rate: int,
    length: int,
    state: NoiseReferenceState,
) -> Tuple[np.ndarray, NoiseReferenceState]:
    """Renders noise one shift-register clock at a time, as the hardware produces it.

    Each output sample covers ``shift_rate / sample_rate`` register steps. A sample that
    spans no step holds the current output bit; a sample that spans one or more steps
    takes the mean of the bits those steps produce. The bipolar result maps a set bit to
    ``+1`` and a clear bit to ``-1``.

    This is the oracle the vectorized ``LFSRTimer`` is measured against, so it stays
    deliberately literal.

    Args:
        period_index: Index into ``NOISE_PERIODS``.
        short: Whether the register runs in its 93-step short mode.
        sample_rate: Output sample rate in Hz.
        length: Number of samples to render.
        state: The register and clock phase to resume from.

    Returns:
        Tuple[np.ndarray, NoiseReferenceState]: The float32 frame and the state the next
            render continues from.
    """
    clocks_per_sample = shift_rate(period_index) / float(sample_rate)
    frame = np.zeros(length, dtype=np.float32)

    lfsr = state.lfsr
    clock = state.clock

    for index in range(length):
        next_clock = clock + clocks_per_sample
        steps = int(np.floor(next_clock)) - int(np.floor(clock))

        if steps == 0:
            level = float(lfsr & 1)
        else:
            total = 0
            for _ in range(steps):
                lfsr = step_lfsr(lfsr, short)
                total += lfsr & 1
            level = total / float(steps)

        frame[index] = 2.0 * level - 1.0
        clock = next_clock

    return frame, NoiseReferenceState(lfsr=lfsr, clock=clock % 1.0)
