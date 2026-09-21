from typing import List, Sequence, Tuple

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.specification.compression import MAX_PHRASE_LENGTH
from sampletones_tools.codec.study.corpus.song import StudySlice, StudySong
from sampletones_tools.codec.study.layouts.layout import PlaneLayout
from sampletones_tools.codec.study.layouts.tone import tone_planes


def layout_planes(
    song: StudySong,
    layout: PlaneLayout,
) -> Tuple[bytes, ...]:
    """Every plane of a song written under a layout, in the order the song block writes them.

    Args:
        song: The song.
        layout: How each tone channel's divider is written.

    Returns:
        Tuple[bytes, ...]: The planes; a flagged bend plane covers fewer values than the song's ticks.
    """
    tones = tuple(song.planes.of(channel) for channel in ChannelName.items() if channel in TONE_CHANNELS)
    planes: List[bytes] = []
    for channel, notes in zip(tones, song.notes, strict=True):
        planes.extend(tone_planes(channel, notes, song.pitches, layout))

    planes.extend(song.planes.of(ChannelName.NOISE))
    return tuple(planes)


def layout_seeds(
    slices: Sequence[StudySlice],
    pitches: PitchTable,
    layout: PlaneLayout,
) -> Tuple[Phrase, ...]:
    """The phrases a song's voices offer the dictionary, each slice written under a layout.

    A slice offers every plane it turns over, as ``phrases_from_project`` does, so a layout's
    dictionary is seeded by the same shapes its song's planes repeat.

    Args:
        slices: The song's voices, one channel at a time.
        pitches: The timer each pitch sounds at.
        layout: How each tone channel's divider is written.

    Returns:
        Tuple[Phrase, ...]: The phrases, in slice order.
    """
    phrases: List[Phrase] = []
    for study_slice in slices:
        planes = (
            tone_planes(study_slice.planes, study_slice.notes, pitches, layout)
            if study_slice.channel in TONE_CHANNELS
            else study_slice.planes
        )

        phrases.extend(Phrase(body=plane[:MAX_PHRASE_LENGTH]) for plane in planes if len(set(plane)) > 1)

    return tuple(phrases)
