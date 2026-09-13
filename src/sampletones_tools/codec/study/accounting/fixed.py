from dataclasses import dataclass
from typing import Final

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.specification.binary import WORD_SIZE
from sampletones_player.specification.compression import (
    PHRASE_TABLE_ENTRY_SIZE,
    PLANE_COUNT,
)
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_tools.codec.study.accounting.finding import Finding
from sampletones_tools.codec.study.corpus.song import StudySong

TIMER_SIZE: Final[int] = WORD_SIZE


@dataclass(frozen=True)
class FixedOverheads:
    """The bytes a song block pays before any tick is described (H7).

    Attributes:
        header: The song header.
        pitch_table: The pitch table as written, every pitch the format can name.
        pitch_table_used: The pitch table cut at the highest pitch the song sounds.
        loop_entries: The re-entry offsets written whether or not the song loops.
        phrase_offsets: The table of offsets a sequential walk over the phrases could replace.
    """

    header: int
    pitch_table: int
    pitch_table_used: int
    loop_entries: int
    phrase_offsets: int

    @property
    def finding(self) -> Finding:
        """The fixed bytes, and what trimming the table, the entries and the offsets would spare."""
        targeted = self.header + self.pitch_table + self.phrase_offsets
        saving = (self.pitch_table - self.pitch_table_used) + self.loop_entries + self.phrase_offsets
        return Finding(targeted, saving)


def fixed_overheads(
    song: StudySong,
    compressed: CompressedPlanes,
) -> FixedOverheads:
    """Accounts for the bytes a song block pays regardless of its length.

    Args:
        song: The song, for the pitches it sounds.
        compressed: The encoding, for the phrases it holds.

    Returns:
        FixedOverheads: The fixed bytes, part by part.
    """
    highest = max(max(channel.value) for channel in (song.planes.pulse1, song.planes.pulse2, song.planes.triangle))
    return FixedOverheads(
        header=SONG_HEADER_SIZE,
        pitch_table=len(song.pitches.data),
        pitch_table_used=TIMER_SIZE * (highest + 1),
        loop_entries=WORD_SIZE * PLANE_COUNT,
        phrase_offsets=PHRASE_TABLE_ENTRY_SIZE * len(compressed.phrases),
    )
