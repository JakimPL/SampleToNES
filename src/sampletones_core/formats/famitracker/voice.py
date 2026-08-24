from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, Optional, Tuple

from pydantic import ValidationError

from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    DEFAULT_SEQUENCE_SETTING,
    LOOP_FROM_START,
    NO_RELEASE_POINT,
    SequenceKind,
)
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.exceptions import InvalidInstrumentValuesError

Sequences = Dict[SequenceKind, InstrumentSequence]


class InstrumentOmission(StrEnum):
    """What a tracker instrument states beyond the envelopes and loop points a voice holds."""

    PITCH = "pitch"
    HI_PITCH = "hi_pitch"
    RELEASE_POINT = "release_point"
    ARPEGGIO_MODE = "arpeggio_mode"


@dataclass(frozen=True)
class ImportedVoice:
    """A voice made from a tracker instrument, beside what the instrument stated past it.

    Attributes:
        voice: The instrument voice the envelopes describe.
        omissions: What the tracker instrument carried that the voice leaves to the file.
    """

    voice: Instrument
    omissions: Tuple[InstrumentOmission, ...]


def instrument_to_voice(instrument: Instrument2A03) -> ImportedVoice:
    """Makes a voice from a FamiTracker instrument, and names what the instrument stated past it.

    A voice carries a volume, an arpeggio and a duty-cycle envelope, each with the item it
    repeats from, so those come across as they stand. A tracker instrument states more than that
    — a pitch bend, a release segment, an arpeggio mode — and each of those is reported, so a
    reader learns what the file held.

    The voice measures its arpeggio against the pitch a voice added by hand rests at, since a
    tracker instrument sounds at whatever note a row names it with.

    Args:
        instrument: The instrument a ``.fti`` file or a module holds.

    Returns:
        ImportedVoice: The voice, and what it leaves to the instrument it came from.

    Raises:
        InvalidInstrumentValuesError: If a sequence carries an item outside the range the
            dimension it feeds holds.
    """
    sequences = instrument.sequences

    return ImportedVoice(
        voice=_voice(instrument.name, sequences),
        omissions=_omissions(sequences),
    )


def _voice(
    name: str,
    sequences: Sequences,
) -> Instrument:
    try:
        envelopes = InstrumentEnvelopes(
            volume=_envelope(sequences[SequenceKind.VOLUME]),
            arpeggio=_envelope(sequences[SequenceKind.ARPEGGIO]),
            duty_cycle=_envelope(sequences[SequenceKind.DUTY]),
        )
    except ValidationError as exception:
        raise InvalidInstrumentValuesError(
            f'Failed to read the envelopes of instrument "{name}" due to validation error: {exception}',
            exception,
        ) from exception

    return Instrument(
        name=name,
        envelopes=envelopes,
    )


def _envelope(sequence: InstrumentSequence) -> Envelope[int]:
    """One dimension as the voice holds it, carrying the point that sequence repeats from.

    Args:
        sequence: The sequence the file states for this dimension.

    Returns:
        Envelope[int]: Its items and its own loop point, empty where the file writes nothing.
    """
    return Envelope[int](
        items=sequence.items,
        loop_point=_loop_point(sequence),
    )


def _loop_point(sequence: InstrumentSequence) -> Optional[int]:
    if sequence.loop_point < LOOP_FROM_START or sequence.loop_point >= len(sequence.items):
        return None

    return sequence.loop_point


def _omissions(sequences: Sequences) -> Tuple[InstrumentOmission, ...]:
    arpeggio = sequences[SequenceKind.ARPEGGIO]
    held = {
        InstrumentOmission.PITCH: sequences[SequenceKind.PITCH].enabled,
        InstrumentOmission.HI_PITCH: sequences[SequenceKind.HI_PITCH].enabled,
        InstrumentOmission.RELEASE_POINT: _holds_release_point(sequences),
        InstrumentOmission.ARPEGGIO_MODE: arpeggio.enabled and arpeggio.setting != DEFAULT_SEQUENCE_SETTING,
    }

    return tuple(omission for omission, stated in held.items() if stated)


def _holds_release_point(sequences: Sequences) -> bool:
    return any(sequence.enabled and sequence.release_point != NO_RELEASE_POINT for sequence in sequences.values())
