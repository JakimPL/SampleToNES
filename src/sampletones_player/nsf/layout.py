from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Sequence, Tuple

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.song import Song
from sampletones_player.specification.compression import (
    PHRASE_LENGTH_SIZE,
    PHRASE_TABLE_COUNT_SIZE,
    PHRASE_TABLE_ENTRY_SIZE,
)
from sampletones_player.specification.song import SONG_HEADER_SIZE

FIRST_TICK: Final[int] = 0
NAME_SEPARATOR: Final[str] = "_"


def _running(start: int, sizes: Sequence[int]) -> Tuple[int, ...]:
    offsets = []
    offset = start
    for size in sizes:
        offsets.append(offset)
        offset += size

    return tuple(offsets)


@dataclass(frozen=True)
class SongLayout:
    """Where each part of a song block begins, every offset counted from the block's first byte.

    The block is written and read through these offsets alone, which is what lets each part grow
    with the song it carries: a header states where the tables and the streams lie, a phrase
    entry states where its body lies, and the driver reaches any of them by adding the offset to
    the address the song loaded at.

    Attributes:
        timer_table: Where the timer each pitch sounds at begins.
        phrase_table: Where the dictionary's count and entries begin.
        bodies: Where each phrase's length byte lies, in id order.
        streams: Where each plane's token stream begins, in song-block order.
        loop_entries: Where each plane's stream is re-entered once the song repeats.
        size: The bytes the whole block takes.
    """

    timer_table: int
    phrase_table: int
    bodies: Tuple[int, ...]
    streams: Tuple[int, ...]
    loop_entries: Tuple[int, ...]
    size: int

    @classmethod
    def of(cls, song: Song) -> SongLayout:
        """Lays a song out into the block the driver plays it from.

        Args:
            song: The compressed planes, the timer table and the clock to lay out.

        Returns:
            SongLayout: Where each part of the block begins.

        Raises:
            ValueError: If a stream spans the song's loop tick rather than starting a token there.
        """
        phrases = song.planes.phrases
        streams = song.planes.streams
        body_sizes = [PHRASE_LENGTH_SIZE + phrase.length for phrase in phrases.phrases]
        stream_sizes = [len(stream) for stream in streams]

        timer_table = SONG_HEADER_SIZE
        phrase_table = timer_table + len(song.pitches.data)
        bodies = phrase_table + cls._table_size(phrases)
        stream_start = bodies + sum(body_sizes)

        stream_offsets = _running(stream_start, stream_sizes)
        entered = song.planes.entries(FIRST_TICK if song.loop_tick is None else song.loop_tick)
        return cls(
            timer_table=timer_table,
            phrase_table=phrase_table,
            bodies=_running(bodies, body_sizes),
            streams=stream_offsets,
            loop_entries=tuple(offset + entry for offset, entry in zip(stream_offsets, entered)),
            size=stream_start + sum(stream_sizes),
        )

    @staticmethod
    def _table_size(phrases: PhraseTable) -> int:
        return PHRASE_TABLE_COUNT_SIZE + PHRASE_TABLE_ENTRY_SIZE * len(phrases)

    @property
    def stated(self) -> Tuple[Tuple[str, int], ...]:
        """Every offset the block states, each under the name of what it points at."""
        return (
            ("timer table", self.timer_table),
            ("phrase table", self.phrase_table),
            *((f"phrase {phrase_id}", offset) for phrase_id, offset in enumerate(self.bodies)),
            *self._named(self.streams, "stream"),
            *self._named(self.loop_entries, "loop entry"),
        )

    @staticmethod
    def _named(offsets: Sequence[int], part: str) -> Tuple[Tuple[str, int], ...]:
        return tuple(
            (f"{plane.replace(NAME_SEPARATOR, ' ')} {part}", offset)
            for plane, offset in zip(PlaneOrder.names(), offsets)
        )
