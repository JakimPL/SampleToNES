from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.features.limits import within_limit
from sampletones_core.formats.bitphase.model.instrument import InstrumentMacro
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH


def stored_envelope(feature_key: FeatureKey, envelope: Envelope[int]) -> Envelope[int]:
    """One dimension as a Bitphase instrument holds it, within the values a macro stores.

    The value limit belongs to the tracker, and :func:`within_limit` is the rule every format
    shortens a dimension by.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        Envelope[int]: The dimension within the values a macro holds.
    """
    return within_limit(feature_key, envelope, MAX_MACRO_LENGTH)


def macro(envelope: Envelope[int]) -> InstrumentMacro:
    """One dimension as the macro Bitphase reads it from.

    Playback circles from the macro's loop index once the values run out, so a dimension
    holding its final value states that value's own index, and one circling from a point
    states the point. A dimension longer than a macro stores keeps its opening values.

    Args:
        envelope: The dimension to write.

    Returns:
        InstrumentMacro: The macro carrying that dimension.

    Raises:
        ValueError: If the dimension writes no value at all.
    """
    stored = envelope.limited(MAX_MACRO_LENGTH)
    loop = stored.loop_point if stored.loop_point is not None else len(stored.items) - 1
    return InstrumentMacro(values=stored.items, loop=loop)
