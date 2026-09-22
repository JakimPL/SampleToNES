from dataclasses import dataclass
from typing import Container, Final, Generic, List, Tuple, TypeVar

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_on import NoteOn

DocumentT = TypeVar("DocumentT")


@dataclass(frozen=True)
class SkippedRow:
    """A note-on the target format has no instrument for, which the export wrote as a note cut.

    A voice sounds on the channels its instruments cover, so a row naming it elsewhere plays
    nothing in the song either. The row is named by where the reader finds it in the tracker.

    Attributes:
        voice_id: The voice the row names.
        channel: The channel the row stands on.
        order_position: The frame of the order the row stands in.
        row_index: The row's position within its pattern.
    """

    voice_id: str
    channel: ChannelName
    order_position: int
    row_index: int


NO_SKIPPED_ROWS: Final[Tuple[SkippedRow, ...]] = ()


@dataclass(frozen=True)
class BuiltDocument(Generic[DocumentT]):
    """A format's document with the rows its build left silent.

    Attributes:
        document: What the format serializes.
        skipped_rows: The rows written as a note cut for lack of an instrument.
    """

    document: DocumentT
    skipped_rows: Tuple[SkippedRow, ...]


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
                            )
                        )

    return tuple(skipped)
