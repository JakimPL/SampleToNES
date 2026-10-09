from dataclasses import dataclass
from typing import Final, Literal, Mapping, Tuple

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.truncation import StoredLength, is_shortened
from sampletones_core.exports.format import ExportFormat
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.truncation import (
    document_stored_length,
    preset_stored_length,
)
from sampletones_core.formats.famitracker.sequences.features import stored_length

TrackerFormat = Literal[
    ExportFormat.FAMITRACKER,
    ExportFormat.BITPHASE,
    ExportFormat.BITPHASE_PRESET,
]

FORMAT_STORED_LENGTHS: Final[Mapping[TrackerFormat, StoredLength]] = {
    ExportFormat.FAMITRACKER: stored_length,
    ExportFormat.BITPHASE: document_stored_length,
    ExportFormat.BITPHASE_PRESET: preset_stored_length,
}


@dataclass(frozen=True)
class FormatShortening:
    """What one tracker format keeps of a dimension it stores shorter.

    Attributes:
        export_format: The format that shortens the dimension.
        kept: The items it keeps.
    """

    export_format: TrackerFormat
    kept: int


def format_shortenings(
    feature_key: FeatureKey,
    envelope: Envelope[int],
) -> Tuple[FormatShortening, ...]:
    """Every tracker format that shortens a dimension, with the items each keeps.

    Each format stores a bounded number of items per dimension, and each states its bound in its
    own package, so a reader editing an envelope sees what every tracker export would keep of it
    before one is made.

    Args:
        feature_key: The dimension being written.
        envelope: The dimension as the instrument carries it.

    Returns:
        Tuple[FormatShortening, ...]: One entry per format that shortens the dimension, in the order
            the formats are listed, and none where every format stores it whole.
    """
    return tuple(
        FormatShortening(
            export_format=export_format,
            kept=stored(feature_key, envelope),
        )
        for export_format, stored in FORMAT_STORED_LENGTHS.items()
        if is_shortened(feature_key, envelope, stored)
    )
