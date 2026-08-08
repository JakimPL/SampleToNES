from typing import Tuple

from sampletones_shared.display import UNLIMITED_FRAME_RATE, Resolution


def available_resolutions(
    resolutions: Tuple[Resolution, ...],
    *,
    min_width: int,
    min_height: int,
    max_width: int,
    max_height: int,
) -> Tuple[Resolution, ...]:
    """The sizes a window may open at within the given bounds, in the order they are offered.

    A size is offered when it meets the window's minimum and stays inside the bound the caller
    measures against — the usable area of the monitor the window sits on — so the window opens
    at the size that was picked and comes back at it after a restart. The monitor's own
    resolution is reached by going fullscreen.

    Args:
        resolutions: The sizes the build offers, in the order a combo shows them.
        min_width: Narrowest width the window opens at.
        min_height: Shortest height the window opens at.
        max_width: Widest width the window is given room for.
        max_height: Tallest height the window is given room for.

    Returns:
        Tuple[Resolution, ...]: The sizes to offer, or the window minimum alone where the bounds
            leave room for none of them.
    """
    offered = tuple(
        resolution
        for resolution in resolutions
        if resolution.reaches(min_width, min_height) and resolution.fits_within(max_width, max_height)
    )
    if offered:
        return offered

    return (Resolution(width=min_width, height=min_height),)


def resolution_labels(resolutions: Tuple[Resolution, ...]) -> Tuple[str, ...]:
    return tuple(str(resolution) for resolution in resolutions)


def frame_rate_label(frame_rate: int, *, unlimited_label: str) -> str:
    """The label a frame rate shows under, naming zero as the unlimited setting."""
    return unlimited_label if frame_rate == UNLIMITED_FRAME_RATE else str(frame_rate)


def frame_rate_labels(frame_rates: Tuple[int, ...], *, unlimited_label: str) -> Tuple[str, ...]:
    return tuple(frame_rate_label(frame_rate, unlimited_label=unlimited_label) for frame_rate in frame_rates)


def nearest_frame_rate(max_fps: int, frame_rates: Tuple[int, ...]) -> int:
    """The offered frame rate a stored preference selects, the closest one it lies between.

    A preference outlives the list that was offered when it was written, so a stored value the
    build has since dropped still selects an entry the combo shows.

    Raises:
        ValueError: when no frame rate is offered.
    """
    if not frame_rates:
        raise ValueError("Selecting a frame rate requires at least one offered rate")

    if max_fps in frame_rates:
        return max_fps

    return min(frame_rates, key=lambda frame_rate: (abs(frame_rate - max_fps), frame_rate))


def nearest_resolution(
    width: int,
    height: int,
    resolutions: Tuple[Resolution, ...],
) -> Resolution:
    """The offered size a window of the given dimensions selects, the closest one by area.

    Raises:
        ValueError: when no size is offered.
    """
    if not resolutions:
        raise ValueError("Selecting a resolution requires at least one offered size")

    return min(
        resolutions,
        key=lambda resolution: (
            abs(resolution.width - width) + abs(resolution.height - height),
            resolution.width,
            resolution.height,
        ),
    )
