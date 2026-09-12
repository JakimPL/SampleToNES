from dataclasses import dataclass
from enum import StrEnum

from codec_study.measure import Encoder


class VariantKind(StrEnum):
    """What a variant changes to earn its bytes.

    Attributes:
        BASELINE: The production codec as it stands.
        ENCODER: A change to how the encoder chooses, readable by the driver as it stands.
        FORMAT: A change to the token grammar, which the driver has to learn.
    """

    BASELINE = "baseline"
    ENCODER = "encoder"
    FORMAT = "format"


@dataclass(frozen=True)
class Variant:
    """One way of encoding a song the study prices against the baseline.

    Attributes:
        name: What the variant is called in a report.
        hypothesis: The hypothesis the variant measures, by its label in the plan.
        kind: What the variant changes.
        note: What the driver would have to do, where the variant changes the format.
        encode: What the variant writes a song as.
    """

    name: str
    hypothesis: str
    kind: VariantKind
    note: str
    encode: Encoder
