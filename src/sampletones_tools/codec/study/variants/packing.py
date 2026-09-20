from dataclasses import replace
from functools import partial
from typing import Final, Tuple

from sampletones_tools.codec.study.packing.encode import encode_packed
from sampletones_tools.codec.study.packing.grammar import encode_packed_grammar
from sampletones_tools.codec.study.packing.scheme import PackingScheme
from sampletones_tools.codec.study.sandbox.grammar import BASELINE_GRAMMAR, Grammar
from sampletones_tools.codec.study.variants.sandbox import (
    DEFAULT_COUNT,
    DEFAULT_COUNT_COSTS,
    DEFAULT_COUNT_NOTE,
    WIDE_HOLD,
    WIDE_HOLD_NOTE,
)
from sampletones_tools.codec.study.variants.variant import Variant, VariantKind

PLANE_REPEATS: Final[str] = "R1"
DRIVER_NOTE: Final[str] = (
    "a plane's byte carries a repeat count in the bits its register leaves alone; the driver "
    "masks the symbol, ors the bits the hardware fixes, and counts a repeat down by subtracting "
    "one step, advancing a symbol only where the count runs out"
)
FIXED_NOTE: Final[str] = f"{DRIVER_NOTE}. The masks follow from the plane, so the block states none"
FITTED_NOTE: Final[str] = (
    f"{DRIVER_NOTE}. The block states each plane's mask and the bits its register fixes, "
    "two bytes a plane, and the encoder reads them off the plane's own values"
)
TABLE_NOTE: Final[str] = (
    f"{DRIVER_NOTE}, and the value is reached through a table of the plane's own values by one "
    "indexed load. The block states each table, and a transposed phrase shifts a code"
)

PACKING_VARIANTS: Final[Tuple[Variant, ...]] = (
    Variant(
        name="packed-fixed",
        hypothesis=PLANE_REPEATS,
        kind=VariantKind.FORMAT,
        note=FIXED_NOTE,
        encode=partial(encode_packed, scheme=PackingScheme.FIXED),
        needs_seeds=False,
    ),
    Variant(
        name="packed-fitted",
        hypothesis=PLANE_REPEATS,
        kind=VariantKind.FORMAT,
        note=FITTED_NOTE,
        encode=partial(encode_packed, scheme=PackingScheme.FITTED),
        needs_seeds=False,
    ),
    Variant(
        name="packed-table",
        hypothesis=PLANE_REPEATS,
        kind=VariantKind.FORMAT,
        note=TABLE_NOTE,
        encode=partial(encode_packed, scheme=PackingScheme.TABLE),
        needs_seeds=False,
    ),
)


WIDE_HOLD_GRAMMAR: Final[Grammar] = replace(BASELINE_GRAMMAR, wide_hold=True)
GRADUATES_GRAMMAR: Final[Grammar] = replace(
    BASELINE_GRAMMAR,
    wide_hold=True,
    default_counts=True,
    costs=DEFAULT_COUNT_COSTS,
)
BEST_SCHEME: Final[PackingScheme] = PackingScheme.TABLE

COMBINED_VARIANTS: Final[Tuple[Variant, ...]] = (
    Variant(
        name="packed-table+wide-hold",
        hypothesis=f"{PLANE_REPEATS}+{WIDE_HOLD}",
        kind=VariantKind.FORMAT,
        note=f"{TABLE_NOTE}. {WIDE_HOLD_NOTE}",
        encode=partial(encode_packed_grammar, scheme=BEST_SCHEME, grammar=WIDE_HOLD_GRAMMAR),
        needs_seeds=False,
    ),
    Variant(
        name="packed-table+graduates",
        hypothesis=f"{PLANE_REPEATS}+{WIDE_HOLD}+{DEFAULT_COUNT}",
        kind=VariantKind.FORMAT,
        note=f"{TABLE_NOTE}. {WIDE_HOLD_NOTE}; {DEFAULT_COUNT_NOTE}",
        encode=partial(encode_packed_grammar, scheme=BEST_SCHEME, grammar=GRADUATES_GRAMMAR),
        needs_seeds=False,
    ),
    Variant(
        name="packed-fixed+graduates",
        hypothesis=f"{PLANE_REPEATS}+{WIDE_HOLD}+{DEFAULT_COUNT}",
        kind=VariantKind.FORMAT,
        note=f"{FIXED_NOTE}. {WIDE_HOLD_NOTE}; {DEFAULT_COUNT_NOTE}",
        encode=partial(encode_packed_grammar, scheme=PackingScheme.FIXED, grammar=GRADUATES_GRAMMAR),
        needs_seeds=False,
    ),
)
