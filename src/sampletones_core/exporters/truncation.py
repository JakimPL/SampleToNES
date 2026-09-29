from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final, List, Optional, Sequence

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope

ONE_INSTRUMENT: Final[int] = 1

StoredLength = Callable[[FeatureKey, Envelope[int]], int]


@dataclass(frozen=True)
class EnvelopeTruncation:
    """The frames a target format's item limit leaves out of the instruments one export wrote.

    Attributes:
        frames: The frame count a shortened instrument carries.
        source_frames: The longest envelope the export was given.
        instruments: How many written instruments were shortened.
    """

    frames: int
    source_frames: int
    instruments: int

    @classmethod
    def summarize(
        cls,
        truncations: Sequence[Optional[EnvelopeTruncation]],
    ) -> Optional[EnvelopeTruncation]:
        """Gathers the per-instrument shortenings of one export into a single report.

        Args:
            truncations: One entry per written instrument, ``None`` where it fit whole.

        Returns:
            Optional[EnvelopeTruncation]: The summary, and ``None`` when every instrument
                carries its whole envelope.
        """
        shortened = [truncation for truncation in truncations if truncation is not None]
        if not shortened:
            return None

        return cls(
            frames=min(truncation.frames for truncation in shortened),
            source_frames=max(truncation.source_frames for truncation in shortened),
            instruments=sum(truncation.instruments for truncation in shortened),
        )


def is_shortened(
    feature_key: FeatureKey,
    envelope: Envelope[int],
    stored_length: StoredLength,
) -> bool:
    """Whether a format leaves items out of one dimension.

    A reader watching an envelope grow and an export reporting what it wrote ask the same question
    of a format, so each format states the length it stores once and both read that answer.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.
        stored_length: The items the format stores of a dimension.

    Returns:
        bool: Whether the format stores fewer items than the dimension carries.
    """
    return stored_length(feature_key, envelope) < len(envelope.items)


def instrument_truncation(
    features: Features,
    stored_length: StoredLength,
) -> Optional[EnvelopeTruncation]:
    """What a format leaves out of one instrument's envelopes.

    The report counts the dimensions the format shortens, so a dimension it stores whole, however
    long, leaves the figures to the others.

    Args:
        features: The per-dimension envelopes describing the instrument.
        stored_length: The items the format stores of a dimension.

    Returns:
        Optional[EnvelopeTruncation]: The longest a shortened dimension stays and the longest it
            was, and ``None`` where every dimension is stored whole.
    """
    stored: List[int] = []
    source: List[int] = []
    for feature_key, envelope in features.envelopes.items():
        if is_shortened(feature_key, envelope, stored_length):
            stored.append(stored_length(feature_key, envelope))
            source.append(len(envelope.items))

    if not stored:
        return None

    return EnvelopeTruncation(
        frames=max(stored),
        source_frames=max(source),
        instruments=ONE_INSTRUMENT,
    )
