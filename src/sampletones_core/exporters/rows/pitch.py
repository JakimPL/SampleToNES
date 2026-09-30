from typing import Final, Iterable

from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH

FLAT_CONTOUR_STEP: Final[int] = 0


def highest_step(steps: Iterable[int]) -> int:
    """The highest semitone step a contour moves its note by, which is none for a contour of no steps.

    Args:
        steps: The contour's steps, one per tick.

    Returns:
        int: The highest of them.
    """
    return max(steps, default=FLAT_CONTOUR_STEP)


def written_pitch(pitch: int, contour_top: int) -> int:
    """The pitch a tracker cell writes for a transposed voice, so its contour sounds where the song's does.

    The song holds every tick's transposed pitch within the range the channels play. A tracker moves
    the written note by the contour's step each tick and holds the result at the same top, so a
    pitch up to the top is written as it is, and one above it is written at the top.

    Below the range a tracker plays every note at its longest period, a little flat of the lowest
    pitch, where the song holds such a tick. A pitch below the range is therefore raised only as far
    as bringing the contour's highest step up to the lowest pitch. Each tick the song plays within
    the range keeps its own note, and a contour lying wholly below the range sounds its highest step
    at the lowest pitch, which for a flat contour is every tick.

    Args:
        pitch: The voice's reference pitch with the row's transpose added.
        contour_top: The highest semitone step the voice's contour moves the note by.

    Returns:
        int: The pitch the cell writes.
    """
    return min(MAX_PITCH, max(pitch, MIN_PITCH - contour_top))
