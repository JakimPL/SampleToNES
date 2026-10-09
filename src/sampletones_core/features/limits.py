from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features.envelope import Envelope, releases


def within_limit(feature_key: FeatureKey, envelope: Envelope[int], limit: int) -> Envelope[int]:
    """One dimension within the items a format stores, the release a volume ends on among them.

    A dimension carries whatever length it was written at, and a format bounds how many items it
    stores of it, so this is where the two meet. A dimension keeps its opening items, and a volume
    dimension ending at silence keeps that silence as its last item — the release is what ends a
    note, so it is the one item worth a place of its own.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.
        limit: The most items the format stores.

    Returns:
        Envelope[int]: The dimension within that limit.
    """
    if feature_key is FeatureKey.VOLUME and releases(envelope):
        return _keeping_release(envelope, limit)

    return envelope.limited(limit)


def _keeping_release(envelope: Envelope[int], limit: int) -> Envelope[int]:
    """This dimension within ``limit`` items, the last of them the release it ends on."""
    if len(envelope.items) <= limit:
        return envelope

    opening = envelope.limited(limit - 1)
    return opening.with_items(opening.items + envelope.items[-1:])
