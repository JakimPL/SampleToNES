from typing import Dict, Final, Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import SILENT_VOLUME
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    FEATURE_KEY_TO_SEQUENCE_KIND,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)

ONE_INSTRUMENT: Final[int] = 1


def features_to_instrument_sequences(features: Features) -> Dict[SequenceKind, InstrumentSequence]:
    """Builds the five 2A03 sequences from a channel slice's envelopes.

    Each dimension becomes an :class:`InstrumentSequence`; one the generator lacks, or one left
    to the channel, becomes a disabled sequence the instrument stores nothing for. Every dimension
    keeps the length it was written at and the item it repeats from, which is how FamiTracker
    advances each sequence on a counter of its own, and each stands within the items the file
    holds — see :func:`stored_envelope`.

    Args:
        features: The per-dimension envelopes describing the slice.

    Returns:
        Dict[SequenceKind, InstrumentSequence]: The sequences, one per dimension FamiTracker holds.
    """
    stored = _stored_envelopes(features)
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
    if feature_key is FeatureKey.VOLUME and _releases(envelope):
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


def _stored_envelopes(features: Features) -> Dict[SequenceKind, Envelope[int]]:
    """Each dimension the slice offers, as the file holds it."""
    return {
        FEATURE_KEY_TO_SEQUENCE_KIND[feature_key]: stored_envelope(feature_key, envelope)
        for feature_key, envelope in features.envelopes.items()
    }


def _releases(envelope: Envelope[int]) -> bool:
    """Whether a volume dimension ends by silencing the note, which is what releases it."""
    return bool(envelope.items) and envelope.items[-1] == SILENT_VOLUME and not envelope.loops


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
