from dataclasses import dataclass
from enum import StrEnum
from typing import Container, Final, Generic, Iterable, List, Optional, Tuple, TypeVar

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_on import NoteOn

DocumentT = TypeVar("DocumentT")


class SkipReason(StrEnum):
    """Why an export wrote a row other than the song plays it.

    ``NO_INSTRUMENT`` is a note-on naming a voice with no instrument on its channel, written as a note
    cut. ``UNREACHED_TRANSPOSE`` is a transpose row moving a sounding note further than the format's
    pitch change reaches, or a row a pattern shared by several frames needs a different change in,
    written without the change there.
    """

    NO_INSTRUMENT = "no_instrument"
    UNREACHED_TRANSPOSE = "unreached_transpose"


@dataclass(frozen=True)
class SkippedRow:
    """A row the export wrote other than the song plays it, named by where the reader finds it in the tracker.

    A voice sounds on the channels its instruments cover, so a note-on naming it elsewhere plays
    nothing in the song either, and the export writes a note cut. A transpose row the format has no
    pitch change for keeps the note at the pitch it had.

    Attributes:
        voice_id: The voice the row names, or the voice it moves.
        channel: The channel the row stands on.
        order_position: The frame of the order the row stands in.
        row_index: The row's position within its pattern.
        reason: What the export wrote in the row's place.
    """

    voice_id: str
    channel: ChannelName
    order_position: int
    row_index: int
    reason: SkipReason


NO_SKIPPED_ROWS: Final[Tuple[SkippedRow, ...]] = ()


@dataclass(frozen=True)
class BuiltDocument(Generic[DocumentT]):
    """A format's document with what its build left out: the rows it silenced and the envelopes it shortened.

    Attributes:
        document: What the format serializes.
        skipped_rows: The rows written as a note cut for lack of an instrument.
        truncation: The instruments the format's value limit shortened, and ``None`` where every
            instrument is held whole.
    """

    document: DocumentT
    skipped_rows: Tuple[SkippedRow, ...]
    truncation: Optional[EnvelopeTruncation]


def find_skipped_rows(
    song: Song,
    instruments: Container[Tuple[str, ChannelName]],
) -> Tuple[SkippedRow, ...]:
    """Finds every row of the song naming a voice on a channel it has no instrument for.

    Rows are listed in the order the song plays them, frame by frame and channel by channel, so a
    pattern the order plays twice reports each of its rows once for every frame it stands in.

    Args:
        song: The arrangement being exported.
        instruments: The ``(voice id, channel)`` pairs the export holds an instrument for.

    Returns:
        Tuple[SkippedRow, ...]: The rows that name a voice without an instrument.
    """
    ordered = {channel: song.ordered_patterns(channel) for channel in ChannelName.items()}
    skipped: List[SkippedRow] = []
    for position in range(song.order_length()):
        for channel in ChannelName.items():
            pattern = ordered[channel][position]
            if pattern is None:
                continue

            for row_index, row in enumerate(pattern.rows[: song.rows_per_pattern]):
                match row.command:
                    case NoteOn() as reference if (reference.voice_id, channel) not in instruments:
                        skipped.append(
                            SkippedRow(
                                voice_id=reference.voice_id,
                                channel=channel,
                                order_position=position,
                                row_index=row_index,
                                reason=SkipReason.NO_INSTRUMENT,
                            )
                        )

    return tuple(skipped)


def in_song_order(rows: Iterable[SkippedRow]) -> Tuple[SkippedRow, ...]:
    """Rows in the order the song plays them: frame by frame, channel by channel, then row by row.

    Args:
        rows: The rows an export reports, gathered in any order.

    Returns:
        Tuple[SkippedRow, ...]: The same rows, in the order the song reaches them.
    """
    channels = ChannelName.items()
    return tuple(
        sorted(
            rows,
            key=lambda skipped: (skipped.order_position, channels.index(skipped.channel), skipped.row_index),
        )
    )
