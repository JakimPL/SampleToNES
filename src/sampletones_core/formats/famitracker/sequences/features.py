from typing import Dict, Final, Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.features.envelope import Envelope, releases
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    BEND_SEQUENCE_KINDS,
    FEATURE_KEY_TO_SEQUENCE_KIND,
    LOOP_FROM_START,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)

ONE_INSTRUMENT: Final[int] = 1
NO_ARPEGGIO_STEP: Final[int] = 0


def features_to_instrument_sequences(features: Features) -> Dict[SequenceKind, InstrumentSequence]:
    """Builds the five 2A03 sequences from a channel slice's envelopes.

    Each dimension becomes an :class:`InstrumentSequence`; one the generator lacks, or one left
    to the channel, becomes a disabled sequence the instrument stores nothing for. Every dimension
    keeps the length it was written at and the item it repeats from, which is how FamiTracker
    advances each sequence on a counter of its own, and each stands within the items the file
    holds — see :func:`stored_envelope`.

    A bend travels with an arpeggio that runs beside it, which is what makes the bend an offset
    from the note — see :func:`_pinning_arpeggio`.

    Args:
        features: The per-dimension envelopes describing the slice.

    Returns:
        Dict[SequenceKind, InstrumentSequence]: The sequences, one per dimension FamiTracker holds.
    """
    stored = _pinned(_stored_envelopes(features))
    return {kind: _sequence(kind, stored.get(kind, Envelope[int]())) for kind in SequenceKind}


def stored_envelope(
    feature_key: FeatureKey,
    envelope: Envelope[int],
) -> Envelope[int]:
    """One dimension as a FamiTracker file holds it, within the items a sequence stores.

    The item limit belongs to the file: an envelope carries whatever length it was written at, and
    this is where a longer one meets what the format stores. A dimension over the limit keeps its
    opening items, and a volume dimension ending at silence keeps that silence as its last item —
    the release is what ends a note, so it is the one item worth a place of its own.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        Envelope[int]: The dimension within the items the file holds.
    """
    if feature_key is FeatureKey.VOLUME and releases(envelope):
        return _keeping_release(envelope, MAX_SEQUENCE_ITEMS)

    return envelope.limited(MAX_SEQUENCE_ITEMS)


def is_shortened(feature_key: FeatureKey, envelope: Envelope[int]) -> bool:
    """Whether a FamiTracker file leaves items out of this dimension.

    A reader watching an envelope grow and an export reporting what it wrote read the same answer,
    so the length a file holds is decided in one place.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        bool: Whether the file holds fewer items than the dimension carries.
    """
    return len(stored_envelope(feature_key, envelope).items) < len(envelope.items)


def features_truncation(features: Features) -> Optional[EnvelopeTruncation]:
    """What a FamiTracker file leaves out of one instrument's envelopes.

    Args:
        features: The per-dimension envelopes describing the instrument.

    Returns:
        Optional[EnvelopeTruncation]: The shortening the file imposes, and ``None`` where every
            dimension is held whole.
    """
    source_frames = features.frame_count
    stored = max(
        (len(envelope.items) for envelope in _stored_envelopes(features).values()),
        default=0,
    )
    if stored >= source_frames:
        return None

    return EnvelopeTruncation(
        frames=stored,
        source_frames=source_frames,
        instruments=ONE_INSTRUMENT,
    )


def _pinned(stored: Dict[SequenceKind, Envelope[int]]) -> Dict[SequenceKind, Envelope[int]]:
    """These sequences with an arpeggio that runs for as long as the bend beside it does.

    FamiTracker walks an instrument's sequences in slot order, and an arpeggio in absolute mode
    reloads the period from the note before the bend sequences add to it. So while the arpeggio
    runs, a bend item is the offset from the note that this project writes it as; once the
    arpeggio halts, the same items start accumulating on the running period instead. Writing an
    arpeggio that covers the bend is what holds the two readings together.

    Args:
        stored: The sequences as the file holds them.

    Returns:
        Dict[SequenceKind, Envelope[int]]: Those sequences, the arpeggio reaching the bend's length.
    """
    bend_length = max((len(stored.get(kind, Envelope[int]()).items) for kind in BEND_SEQUENCE_KINDS), default=0)
    if not bend_length:
        return stored

    return {**stored, SequenceKind.ARPEGGIO: _pinning_arpeggio(stored, bend_length)}


def _pinning_arpeggio(stored: Dict[SequenceKind, Envelope[int]], bend_length: int) -> Envelope[int]:
    """The arpeggio that reloads the note for every tick a bend states an offset for.

    An arpeggio circling from a point runs for as long as the note sounds and needs nothing; one
    playing its items once holds its final note over the remaining ticks, which is the note it
    would rest on anyway; and an instrument writing no arpeggio at all takes one item at its own
    note, repeating.

    Args:
        stored: The sequences as the file holds them.
        bend_length: The ticks the longest bend dimension states.

    Returns:
        Envelope[int]: The arpeggio to write.
    """
    arpeggio = stored.get(SequenceKind.ARPEGGIO, Envelope[int]())
    if arpeggio.loops:
        return arpeggio

    if not arpeggio.items:
        return Envelope[int](items=(NO_ARPEGGIO_STEP,), loop_point=LOOP_FROM_START)

    return arpeggio.resized(max(len(arpeggio.items), bend_length))


def _stored_envelopes(features: Features) -> Dict[SequenceKind, Envelope[int]]:
    """Each dimension the slice offers, as the file holds it."""
    return {
        FEATURE_KEY_TO_SEQUENCE_KIND[feature_key]: stored_envelope(feature_key, envelope)
        for feature_key, envelope in features.envelopes.items()
    }


def _keeping_release(envelope: Envelope[int], limit: int) -> Envelope[int]:
    """This dimension within ``limit`` items, the last of them the release it ends on."""
    if len(envelope.items) <= limit:
        return envelope

    opening = envelope.limited(limit - 1)
    return opening.with_items(opening.items + envelope.items[-1:])


def _sequence(
    kind: SequenceKind,
    envelope: Envelope[int],
) -> InstrumentSequence:
    """One sequence as the file states it, with the item the dimension repeats from."""
    return InstrumentSequence(
        kind=kind,
        items=envelope.items,
        loop_point=envelope.loop_point if envelope.loop_point is not None else NO_LOOP_POINT,
    )
