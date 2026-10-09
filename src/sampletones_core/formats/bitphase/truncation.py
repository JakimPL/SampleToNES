from typing import Optional

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.truncation import EnvelopeTruncation, instrument_truncation
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.macros import stored_envelope


def document_stored_length(feature_key: FeatureKey, envelope: Envelope[int]) -> int:
    """The values a ``.btp`` document holds of one dimension.

    The arpeggio rides a table, which holds a contour of any length, and every other dimension
    rides a macro, which holds its opening values.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        int: The values the document stores.
    """
    if feature_key is FeatureKey.ARPEGGIO:
        return len(envelope.items)

    return len(stored_envelope(feature_key, envelope).items)


def preset_stored_length(feature_key: FeatureKey, envelope: Envelope[int]) -> int:
    """The values an instrument preset holds of one dimension.

    A preset carries macros alone, and the contour folds into the tone offset beside the bend, so
    every dimension keeps the opening values a macro holds.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        int: The values the preset stores.
    """
    return len(stored_envelope(feature_key, envelope).items)


def document_truncation(features: Features) -> Optional[EnvelopeTruncation]:
    """What a ``.btp`` document leaves out of one instrument's envelopes.

    Args:
        features: The per-dimension envelopes describing the instrument.

    Returns:
        Optional[EnvelopeTruncation]: The shortening the document imposes, and ``None`` where
            every dimension is held whole.
    """
    return instrument_truncation(features, document_stored_length)


def preset_truncation(features: Features) -> Optional[EnvelopeTruncation]:
    """What an instrument preset leaves out of one instrument's envelopes.

    Args:
        features: The per-dimension envelopes describing the instrument.

    Returns:
        Optional[EnvelopeTruncation]: The shortening the preset imposes, and ``None`` where every
            dimension is held whole.
    """
    return instrument_truncation(features, preset_stored_length)
