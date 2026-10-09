from typing import Final, Iterable

from sampletones_core.constants.general import MAX_PITCH, MIN_PLAYED_PITCH

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

    The song holds every tick's transposed pitch within the notes a tracker writes, C-0 to B-7 (see
    :func:`played_pitch`). A tracker moves the written note by the contour's step each tick and holds
    the result within the same notes, so a pitch inside them is written as it is, and one above the
    top is written at the top.

    A tracker writes no note below C-0, so a pitch below it is raised only as far as bringing the
    contour's highest step up to C-0. Each tick the song plays within the range keeps its own note,
    and a contour lying wholly below the range sounds its highest step at C-0, which for a flat
    contour is every tick.

    Args:
        pitch: The voice's reference pitch with the row's transpose added.
        contour_top: The highest semitone step the voice's contour moves the note by.

    Returns:
        int: The pitch the cell writes.
    """
    return min(MAX_PITCH, max(pitch, MIN_PLAYED_PITCH - contour_top))
