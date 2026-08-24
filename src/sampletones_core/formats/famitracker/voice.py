from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, Optional, Tuple

from pydantic import ValidationError

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
    """What a tracker instrument states beyond the envelopes and the one loop point a voice holds."""

    PITCH = "pitch"
    HI_PITCH = "hi_pitch"
    RELEASE_POINT = "release_point"
    ARPEGGIO_MODE = "arpeggio_mode"
    SEQUENCE_LOOP_POINTS = "sequence_loop_points"


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

    A voice carries a volume, an arpeggio and a duty-cycle envelope, and one loop point every
    dimension follows, so those come across as they stand. A tracker instrument states more than
    that — a pitch bend, a release segment, an arpeggio mode, a loop point of its own per
    sequence — and each of those is reported, so a reader learns what the file held.

    The voice measures its arpeggio against the roots a voice added by hand rests on, since a
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
    governing = _governing_sequence(sequences)

    return ImportedVoice(
        voice=_voice(instrument.name, sequences, _loop_point(governing)),
        omissions=_omissions(sequences, governing),
    )


def _voice(
    name: str,
    sequences: Sequences,
    loop_point: Optional[int],
) -> Instrument:
    try:
        envelopes = InstrumentEnvelopes(
            volume=sequences[SequenceKind.VOLUME].items,
            arpeggio=sequences[SequenceKind.ARPEGGIO].items,
            duty_cycle=sequences[SequenceKind.DUTY].items,
        )
    except ValidationError as exception:
        raise InvalidInstrumentValuesError(
            f'Failed to read the envelopes of instrument "{name}" due to validation error: {exception}',
            exception,
        ) from exception

    return Instrument(
        name=name,
        envelopes=envelopes,
        loop_point=loop_point,
    )


def _governing_sequence(sequences: Sequences) -> Optional[InstrumentSequence]:
    """The sequence whose loop point the whole voice adopts.

    A voice repeats every dimension from one tick, so one sequence states the point the rest
    follow. The volume sequence governs wherever it is written, since it is the one that shapes
    a held note; otherwise the first sequence the instrument writes does.
    """
    volume = sequences[SequenceKind.VOLUME]
    if volume.enabled:
        return volume

    return next(
        (sequence for sequence in sequences.values() if sequence.enabled),
        None,
    )


def _loop_point(governing: Optional[InstrumentSequence]) -> Optional[int]:
    if governing is None or governing.loop_point < LOOP_FROM_START:
        return None

    return governing.loop_point


def _omissions(
    sequences: Sequences,
    governing: Optional[InstrumentSequence],
) -> Tuple[InstrumentOmission, ...]:
    arpeggio = sequences[SequenceKind.ARPEGGIO]
    held = {
        InstrumentOmission.PITCH: sequences[SequenceKind.PITCH].enabled,
        InstrumentOmission.HI_PITCH: sequences[SequenceKind.HI_PITCH].enabled,
        InstrumentOmission.RELEASE_POINT: _holds_release_point(sequences),
        InstrumentOmission.ARPEGGIO_MODE: arpeggio.enabled and arpeggio.setting != DEFAULT_SEQUENCE_SETTING,
        InstrumentOmission.SEQUENCE_LOOP_POINTS: _holds_separate_loop_points(
            sequences,
            governing,
        ),
    }

    return tuple(omission for omission, stated in held.items() if stated)


def _holds_release_point(sequences: Sequences) -> bool:
    return any(sequence.enabled and sequence.release_point != NO_RELEASE_POINT for sequence in sequences.values())


def _holds_separate_loop_points(
    sequences: Sequences,
    governing: Optional[InstrumentSequence],
) -> bool:
    if governing is None:
        return False

    return any(sequence.enabled and sequence.loop_point != governing.loop_point for sequence in sequences.values())
