from typing import Final

PERCENT_SCALE: Final[int] = 100


def format_percent(fraction: float) -> str:
    """Renders a 0-1 fraction as a whole-percent label, clamped to the bar's displayable range."""
    clamped = max(0.0, min(1.0, fraction))
    return f"{int(clamped * PERCENT_SCALE)}%"
