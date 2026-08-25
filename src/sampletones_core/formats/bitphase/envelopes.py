from dataclasses import dataclass
from typing import Final, Iterable, Tuple

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.model.instrument import NesInstrumentRow
from sampletones_core.formats.bitphase.notes import noise_arpeggio_to_table_offset
from sampletones_core.formats.bitphase.specification.instruments import (
    FLAT_PULSE_WIDTH,
    LOOP_FROM_START,
    MAX_VOLUME_OR_RATE,
    NO_TABLE_OFFSET,
    NOISE_MODE_LONG,
    NOISE_MODE_SHORT,
    SILENT_VOLUME,
)

SILENT_ROW: Final[NesInstrumentRow] = NesInstrumentRow(
    pulse_width=FLAT_PULSE_WIDTH,
    volume_or_rate=SILENT_VOLUME,
)


@dataclass(frozen=True)
class ChannelEnvelopes:
    """One channel slice expressed the way Bitphase plays it back.

    The instrument rows and the table rows advance on their own per-tick counters, so
    they share a length and a loop point and stay in step for as long as the note
    sounds.

    Attributes:
        rows: Instrument rows, one per engine tick.
        table_rows: Semitone offsets, one per engine tick.
        loop: Row both lists return to once they run off the end.
    """

    rows: Tuple[NesInstrumentRow, ...]
    table_rows: Tuple[int, ...]
    loop: int


def _pulse_width(channel: ChannelName, duty_cycle: int) -> int:
    """Reads a duty-cycle item as the field the channel uses it for.

    A square channel takes it as the duty itself; the noise channel takes any nonzero
    value as its short LFSR mode; the triangle channel plays one fixed waveform.
    """
    match channel:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            return duty_cycle
        case ChannelName.NOISE:
            return NOISE_MODE_SHORT if duty_cycle else NOISE_MODE_LONG
        case ChannelName.TRIANGLE:
            return FLAT_PULSE_WIDTH


def _table_offset(channel: ChannelName, arpeggio: int) -> int:
    if channel == ChannelName.NOISE:
        return noise_arpeggio_to_table_offset(arpeggio)

    return arpeggio


def _held_volume(frames: int) -> Tuple[int, ...]:
    """The volume envelope of a slice whose level the channel governs.

    Bitphase combines each row's level with the pattern's volume column, and a full-level
    row comes out at the column's own level, so an instrument holding one for every frame
    it describes sounds at whatever level the channel carries.

    Args:
        frames: The frames the slice describes.

    Returns:
        Tuple[int, ...]: One full-level item per frame.
    """
    return (MAX_VOLUME_OR_RATE,) * frames


def features_to_envelopes(
    features: Features,
    channel: ChannelName,
) -> ChannelEnvelopes:
    """Converts one channel slice's envelopes into Bitphase instrument and table rows.

    Volume becomes the instrument's per-tick level, the duty cycle becomes the channel's
    waveform field, and the arpeggio becomes the table contour that moves the note. A
    slice that leaves its volume to the channel takes a full level for every frame it
    describes, so the channel governs how loud it sounds. Bitphase reads every dimension out of
    one row, so the instrument returns to the earliest row any dimension repeats from; one whose
    dimensions all halt returns to its last row, resting on the level its volume envelope ends
    with — silence where the slice writes its own, the channel's level where it holds one.

    A slice describing no frame comes back as the one silent row that is the smallest
    instrument Bitphase plays.

    Args:
        features: The per-dimension envelopes describing the slice.
        channel: The NES channel the slice was reconstructed for.

    Returns:
        ChannelEnvelopes: The rows, contour, and loop point describing the slice.
    """
    frames = features.frame_count
    envelopes = {
        feature_key: features.envelopes.get(feature_key, Envelope[int]()).resized(frames)
        for feature_key in (FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE)
    }

    if not frames:
        return ChannelEnvelopes(
            rows=(SILENT_ROW,),
            table_rows=(NO_TABLE_OFFSET,),
            loop=LOOP_FROM_START,
        )

    volumes = envelopes[FeatureKey.VOLUME].items or _held_volume(frames)
    arpeggios = envelopes[FeatureKey.ARPEGGIO].items
    duty_cycles = envelopes[FeatureKey.DUTY_CYCLE].items

    rows = tuple(
        NesInstrumentRow(
            pulse_width=_pulse_width(channel, duty_cycles[frame] if duty_cycles else FLAT_PULSE_WIDTH),
            volume_or_rate=volume,
        )
        for frame, volume in enumerate(volumes)
    )
    contour = arpeggios or (NO_TABLE_OFFSET,) * len(volumes)
    table_rows = tuple(_table_offset(channel, arpeggio) for arpeggio in contour)

    return ChannelEnvelopes(
        rows=rows,
        table_rows=table_rows,
        loop=_loop_row(envelopes.values(), len(rows)),
    )


def _loop_row(envelopes: Iterable[Envelope[int]], rows: int) -> int:
    """The row a Bitphase instrument returns to, which is the earliest any dimension repeats from.

    Bitphase reads every dimension out of one row, so one point serves them all and the earliest
    keeps each dimension sounding what it would have sounded.

    Args:
        envelopes: The dimensions the instrument writes.
        rows: How many rows the instrument holds.

    Returns:
        int: The row to return to, held inside the rows the instrument carries.
    """
    points = [envelope.loop_point for envelope in envelopes if envelope.loop_point is not None]
    if not points:
        return rows - 1

    return min(*points, rows - 1)
