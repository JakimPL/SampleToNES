from sampletones_core.constants.general import (
    APU_CLOCK,
    MAX_TIMER,
    MIN_TIMER,
    TIMER_CYCLE_DIVIDER,
)
from sampletones_shared.utils.arrays import clamp


def frequency_to_timer(frequency: float) -> int:
    """The timer register value a channel sounds a frequency at.

    The APU drives a channel's waveform by dividing its clock by ``16 * (timer + 1)``, so the
    register value is that relation solved for the timer and rounded to the nearest whole
    period. The result stays within the 11 bits the register offers, which is what holds the
    pitches a channel reaches between ``MIN_FREQUENCY`` and ``MAX_FREQUENCY``.

    Args:
        frequency: The frequency in Hz to sound.

    Returns:
        int: The timer value, in ``[0, MAX_TIMER]``. A frequency of 0 Hz or below reads as 0.
    """
    if frequency <= 0:
        return 0

    timer = round(APU_CLOCK / (TIMER_CYCLE_DIVIDER * frequency)) - 1
    return max(0, min(timer, MAX_TIMER))


def get_timer_ticks(timer: int) -> int:
    """The APU cycles one waveform period spans at a timer value.

    Args:
        timer: The timer register value.

    Returns:
        int: The cycles per period, ``16 * (timer + 1)``. A timer of 0 or below reads as 0,
            the span a silent channel covers.
    """
    return (timer + 1) * TIMER_CYCLE_DIVIDER if timer > 0 else 0


def timer_to_frequency(timer: int) -> float:
    """The frequency a channel sounds at a timer register value.

    This is the inverse of `frequency_to_timer`, and reading a timer back through it gives the
    frequency the hardware actually produces — the nearest one the divider reaches, which a
    rendered channel is tuned to.

    Args:
        timer: The timer register value.

    Returns:
        float: The frequency in Hz the divider produces for that timer.
    """
    return APU_CLOCK / (TIMER_CYCLE_DIVIDER * (timer + 1))


def bent_timer(timer: int, offset: int) -> int:
    """The divider a note sounds at once a bend has moved it off its own.

    The sum stays within the 11 bits the register offers and above the divider that stops the
    waveform, which keeps a bend audible wherever it lands.

    Args:
        timer: The divider the note sounds at unbent.
        offset: The divider steps the bend moves it by.

    Returns:
        int: The divider to sound, in ``[MIN_TIMER, MAX_TIMER]``.
    """
    return clamp(timer + offset, MIN_TIMER, MAX_TIMER)
