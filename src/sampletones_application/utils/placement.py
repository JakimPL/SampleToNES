from typing import Tuple


def centered_position(
    center: Tuple[int, int],
    width: int,
    height: int,
) -> Tuple[int, int]:
    """Where a box of this size rests with its middle on ``center``.

    Each axis is held at zero at the least, so a box taller or wider than the space it is
    centered in keeps its top-left corner reachable — which is what leaves a dialog's title bar
    on screen when the reader has made the window smaller than the dialog it raises.

    Args:
        center: The point the box is centered on.
        width: The box's width.
        height: The box's height.

    Returns:
        Tuple[int, int]: The box's top-left corner.
    """
    center_x, center_y = center
    return max(0, round(center_x - width / 2)), max(0, round(center_y - height / 2))
