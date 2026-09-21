from dataclasses import dataclass
from enum import StrEnum


class Anchor(StrEnum):
    """What a tone channel's value plane names for a tick whose divider is bent.

    Attributes:
        NEAREST: The pitch lying nearest the divider, which the divider alone decides.
        NAMED: The note the frame names, which keeps a transposed bend byte for byte; the pitch
            lying nearest stands in where the steps would leave a signed byte.
    """

    NEAREST = "nearest"
    NAMED = "named"


class BendForm(StrEnum):
    """How a tone channel's bend plane covers its ticks.

    Attributes:
        DENSE: A bend every tick, zero where the tick sounds its pitch's own divider.
        FLAGGED_TICKS: The value's top bit marks each tick carrying a bend, and the bend plane
            holds those ticks alone.
        FLAGGED_NOTES: The flag spans a note from its first bent tick to its last, so a bend
            passing through zero keeps the value plane still.
    """

    DENSE = "dense"
    FLAGGED_TICKS = "flagged-ticks"
    FLAGGED_NOTES = "flagged-notes"


@dataclass(frozen=True)
class PlaneLayout:
    """One way of writing a tone channel's divider across its value and bend planes.

    Attributes:
        anchor: What the value plane names.
        form: How the bend plane covers the ticks.
    """

    anchor: Anchor
    form: BendForm
