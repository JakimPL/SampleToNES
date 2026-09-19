from typing import Final, Tuple

from sampletones_shared.constants.music import LIMIT_MIN_PITCH
from sampletones_tools.codec.study.corpus.notes import TONE_ORDER
from sampletones_tools.codec.study.corpus.song import StudySlice

NO_STUDY_SLICES: Final[Tuple[StudySlice, ...]] = ()


def lowest_notes(ticks: int) -> Tuple[bytes, ...]:
    """The notes of a hand-built study song, every tone channel naming the lowest pitch throughout."""
    return (bytes((LIMIT_MIN_PITCH,)) * ticks,) * len(TONE_ORDER)
