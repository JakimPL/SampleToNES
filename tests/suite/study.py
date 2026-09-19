from typing import Final, Tuple

from sampletones_player.compression.planes.channel import ChannelPlanes, TonePlanes
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_shared.constants.music import LIMIT_MIN_PITCH
from sampletones_tools.codec.study.corpus.notes import TONE_ORDER
from sampletones_tools.codec.study.corpus.song import StudySlice

NO_STUDY_SLICES: Final[Tuple[StudySlice, ...]] = ()


def lowest_notes(ticks: int) -> Tuple[bytes, ...]:
    """The notes of a hand-built study song, every tone channel naming the lowest pitch throughout."""
    return (bytes((LIMIT_MIN_PITCH,)) * ticks,) * len(TONE_ORDER)


def resting_planes(ticks: int) -> SongPlanes:
    """A song's planes holding zero throughout, every tone channel bending nowhere."""
    tone = TonePlanes(control=bytes(ticks), value=bytes(ticks), bend=b"")
    return SongPlanes(
        pulse1=tone,
        pulse2=tone,
        triangle=tone,
        noise=ChannelPlanes(control=bytes(ticks), value=bytes(ticks)),
    )
