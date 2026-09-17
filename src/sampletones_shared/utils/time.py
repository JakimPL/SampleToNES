from typing import Final

SECONDS_PER_MINUTE: Final[int] = 60
MINUTES_PER_HOUR: Final[int] = 60


def seconds_from_samples(samples: int, sample_rate: int) -> float:
    """How long a run of samples lasts.

    Args:
        samples: The samples counted.
        sample_rate: The samples one second holds.

    Returns:
        float: The seconds those samples span, zero where the rate names none.
    """
    return samples / sample_rate if sample_rate > 0 else 0.0


def seconds_from_ticks(ticks: int, tick_rate: int) -> float:
    """How long a run of ticks lasts.

    Args:
        ticks: The ticks counted.
        tick_rate: The ticks one second holds.

    Returns:
        float: The seconds those ticks span, zero where the rate names none.
    """
    return ticks / tick_rate if tick_rate > 0 else 0.0


def format_span(seconds: float) -> str:
    """How long something lasts, stated in the largest units it fills.

    A span is read as a quantity — what a render costs, what a song runs to, what an estimate
    has left — so it names its units and rounds down to whole seconds.

    Args:
        seconds: The span measured.

    Returns:
        str: The span as ``1h 02m 13s``, ``2m 13s`` or ``13s``.
    """
    whole_seconds = max(0, int(seconds))
    minutes, seconds_remaining = divmod(whole_seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)

    if hours:
        return f"{hours}h {minutes:02d}m {seconds_remaining:02d}s"
    if minutes:
        return f"{minutes}m {seconds_remaining:02d}s"

    return f"{seconds_remaining}s"


def format_clock(seconds: float, decimals: int) -> str:
    """How far into something a moment stands, stated as a clock reading.

    A position is read against its neighbors — the marks along an axis, a playhead beside them —
    so minutes and seconds carry fixed widths and the hour appears once the run reaches one.
    ``decimals`` states how finely the reading divides a second, which lets a close view name a
    moment the whole seconds beside it would repeat.

    Args:
        seconds: How far in the moment stands.
        decimals: The digits the fraction of a second is stated to.

    Returns:
        str: The moment as ``2:13``, ``1:02:13`` or ``2:13.25``.
    """
    places = max(0, decimals)
    position = round(max(0.0, seconds), places)
    whole_seconds = int(position)
    minutes, seconds_remaining = divmod(whole_seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)

    width = 2 if places == 0 else places + 3
    reading = f"{seconds_remaining + position - whole_seconds:0{width}.{places}f}"

    if hours:
        return f"{hours}:{minutes:02d}:{reading}"

    return f"{minutes}:{reading}"
