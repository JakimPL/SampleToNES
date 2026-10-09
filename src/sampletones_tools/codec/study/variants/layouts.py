from functools import partial
from typing import Final, Tuple

from sampletones_tools.codec.study.layouts.encode import encode_layout
from sampletones_tools.codec.study.layouts.layout import Anchor, BendForm, PlaneLayout
from sampletones_tools.codec.study.variants.variant import Variant, VariantKind

ABSENT_PLANES: Final[str] = "B1"
NAMED_NOTE: Final[str] = "B2"
FLAG_BIT: Final[str] = "B3"
ABSENT_NOTE: Final[str] = (
    "a plane holding zero throughout names a sentinel stream offset, and the driver leaves its value at zero"
)
NAMED_NOTE_NOTE: Final[str] = f"{ABSENT_NOTE}; the value names the frame's note, which the driver reads as it stands"
FLAG_NOTE: Final[str] = (
    f"{ABSENT_NOTE}; bit 7 of the value marks a bent tick, and the bend plane advances only on those ticks"
)


def _layout_variant(
    name: str,
    hypothesis: str,
    note: str,
    layout: PlaneLayout,
) -> Variant:
    return Variant(
        name=name,
        hypothesis=hypothesis,
        kind=VariantKind.FORMAT,
        note=note,
        encode=partial(encode_layout, layout=layout),
        needs_seeds=False,
    )


LAYOUT_VARIANTS: Final[Tuple[Variant, ...]] = (
    _layout_variant("absent-planes", ABSENT_PLANES, ABSENT_NOTE, PlaneLayout(Anchor.NEAREST, BendForm.DENSE)),
    _layout_variant("named-note", NAMED_NOTE, NAMED_NOTE_NOTE, PlaneLayout(Anchor.NAMED, BendForm.DENSE)),
    _layout_variant("flag-ticks", FLAG_BIT, FLAG_NOTE, PlaneLayout(Anchor.NEAREST, BendForm.FLAGGED_TICKS)),
    _layout_variant("flag-notes", FLAG_BIT, FLAG_NOTE, PlaneLayout(Anchor.NEAREST, BendForm.FLAGGED_NOTES)),
    _layout_variant("named-flag-ticks", FLAG_BIT, FLAG_NOTE, PlaneLayout(Anchor.NAMED, BendForm.FLAGGED_TICKS)),
    _layout_variant("named-flag-notes", FLAG_BIT, FLAG_NOTE, PlaneLayout(Anchor.NAMED, BendForm.FLAGGED_NOTES)),
)
