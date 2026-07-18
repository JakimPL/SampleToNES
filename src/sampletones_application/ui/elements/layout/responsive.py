from typing import Final

_BASELINE_VIEWPORT_WIDTH: Final[int] = 1280
_CENTER_WEIGHT: Final[int] = 2


def expanded_side_width(
    base_width: int,
    viewport_width: int,
    side_panel_count: int,
) -> int:
    """Widens a fixed side column as the viewport grows past the design baseline.

    A tab's centre column stretches while its side columns hold fixed widths, so the extra room a
    viewport wider than the 1280 px design baseline offers is shared out with the centre taking
    twice the share of each side. Splitting the surplus ``2 + side_panel_count`` ways and granting
    one share to each side keeps the centre the widest column while the sides breathe on large
    displays. At the baseline the column sits at its configured ``base_width`` and grows only as
    surplus appears above it.
    """
    surplus = viewport_width - _BASELINE_VIEWPORT_WIDTH
    total_weight = _CENTER_WEIGHT + side_panel_count
    expansion = max(0, round(surplus / total_weight))
    return base_width + expansion
