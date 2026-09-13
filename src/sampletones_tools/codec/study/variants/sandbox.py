from dataclasses import replace
from typing import Final, NamedTuple, Tuple

from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.measure import Encoder, Encoding
from sampletones_tools.codec.study.sandbox.costs import (
    DEFAULT_COUNT_OPERANDS,
    DEFAULT_COUNT_SIZE,
    PRODUCTION_COSTS,
    SET_HOLD_BOUND,
    Costs,
)
from sampletones_tools.codec.study.sandbox.encode import encode_grammar
from sampletones_tools.codec.study.sandbox.grammar import BASELINE_GRAMMAR, Grammar
from sampletones_tools.codec.study.variants.baselines import Baselines
from sampletones_tools.codec.study.variants.variant import Variant, VariantKind

WIDE_HOLD: Final[str] = "H1"
SET_HOLD: Final[str] = "H3"
DEFAULT_COUNT: Final[str] = "H4"
HOLD_EDGES: Final[str] = "H9"
DRIVER_UNCHANGED: Final[str] = "driver unchanged"
WIDE_HOLD_NOTE: Final[str] = (
    "a phrase opcode with a zero count; the block count can sit in the idle shift field and "
    "reload in the token fetch, the tick path unchanged"
)
SET_HOLD_NOTE: Final[str] = (
    "a transposed-phrase opcode with a zero count and the value behind it, three bytes; one compare in the token fetch"
)
SET_HOLD_BOUND_NOTE: Final[str] = (
    "a two-byte set-hold needs an opcode of its own, so this bounds what any reallocation of the opcode space reaches"
)
DEFAULT_COUNT_NOTE: Final[str] = (
    "one operand bit says the count is the phrase's own, leaving 31 cheap ids; each table entry "
    "grows by a byte, read once when a phrase is set"
)
COMBINED_NOTE: Final[str] = "every change the free escape carries at once, the escape counting 31 blocks and 31 ticks"

DEFAULT_COUNT_COSTS: Final[Costs] = replace(
    PRODUCTION_COSTS,
    operands=DEFAULT_COUNT_OPERANDS,
    default_entry=DEFAULT_COUNT_SIZE,
)
SET_HOLD_BOUND_COSTS: Final[Costs] = replace(PRODUCTION_COSTS, set_hold=SET_HOLD_BOUND)


class GrammarVariant(NamedTuple):
    """One grammar the sandbox prices, and how the report names it.

    Attributes:
        name: What the variant is called in a report.
        hypothesis: The hypothesis the variant measures, by its label in the plan.
        kind: What the variant changes.
        note: What the driver would have to do.
        grammar: The grammar.
    """

    name: str
    hypothesis: str
    kind: VariantKind
    note: str
    grammar: Grammar


GRAMMAR_VARIANTS: Final[Tuple[GrammarVariant, ...]] = (
    GrammarVariant(
        name="start-hold",
        hypothesis=HOLD_EDGES,
        kind=VariantKind.ENCODER,
        note=f"{DRIVER_UNCHANGED}: every plane is seeded before its first token, so a hold may open a stream",
        grammar=replace(BASELINE_GRAMMAR, start_hold=True),
    ),
    GrammarVariant(
        name="every-hold",
        hypothesis=HOLD_EDGES,
        kind=VariantKind.ENCODER,
        note=DRIVER_UNCHANGED,
        grammar=replace(BASELINE_GRAMMAR, every_length=True),
    ),
    GrammarVariant(
        name="wide-hold",
        hypothesis=WIDE_HOLD,
        kind=VariantKind.FORMAT,
        note=WIDE_HOLD_NOTE,
        grammar=replace(BASELINE_GRAMMAR, wide_hold=True),
    ),
    GrammarVariant(
        name="wide-hold+start-hold",
        hypothesis=f"{WIDE_HOLD}+{HOLD_EDGES}",
        kind=VariantKind.FORMAT,
        note=WIDE_HOLD_NOTE,
        grammar=replace(BASELINE_GRAMMAR, wide_hold=True, start_hold=True),
    ),
    GrammarVariant(
        name="set-hold-3",
        hypothesis=SET_HOLD,
        kind=VariantKind.FORMAT,
        note=SET_HOLD_NOTE,
        grammar=replace(BASELINE_GRAMMAR, set_hold=True),
    ),
    GrammarVariant(
        name="set-hold-2",
        hypothesis=SET_HOLD,
        kind=VariantKind.FORMAT,
        note=SET_HOLD_BOUND_NOTE,
        grammar=replace(BASELINE_GRAMMAR, set_hold=True, costs=SET_HOLD_BOUND_COSTS),
    ),
    GrammarVariant(
        name="default-count",
        hypothesis=DEFAULT_COUNT,
        kind=VariantKind.FORMAT,
        note=DEFAULT_COUNT_NOTE,
        grammar=replace(BASELINE_GRAMMAR, default_counts=True, costs=DEFAULT_COUNT_COSTS),
    ),
    GrammarVariant(
        name="wide-hold+default-count",
        hypothesis=f"{WIDE_HOLD}+{DEFAULT_COUNT}",
        kind=VariantKind.FORMAT,
        note=f"{WIDE_HOLD_NOTE}; {DEFAULT_COUNT_NOTE}",
        grammar=replace(BASELINE_GRAMMAR, wide_hold=True, default_counts=True, costs=DEFAULT_COUNT_COSTS),
    ),
    GrammarVariant(
        name="escape-grammar",
        hypothesis=f"{WIDE_HOLD}+{SET_HOLD}+{DEFAULT_COUNT}+{HOLD_EDGES}",
        kind=VariantKind.FORMAT,
        note=COMBINED_NOTE,
        grammar=replace(
            BASELINE_GRAMMAR,
            start_hold=True,
            wide_hold=True,
            set_hold=True,
            default_counts=True,
            costs=DEFAULT_COUNT_COSTS,
        ),
    ),
)


def grammar_encoder(
    baselines: Baselines,
    grammar: Grammar,
) -> Encoder:
    """An encoder pricing a song under ``grammar`` over its production dictionary.

    Args:
        baselines: Where the production encodings are kept.
        grammar: The grammar.

    Returns:
        Encoder: The encoder.
    """

    def encode(song: StudySong) -> Encoding:
        return encode_grammar(baselines.reference(song), grammar)

    return encode


def grammar_variants(baselines: Baselines) -> Tuple[Variant, ...]:
    """Every grammar the sandbox prices, as the variants a run encodes under.

    Args:
        baselines: Where the production encodings are kept.

    Returns:
        Tuple[Variant, ...]: The variants, in the order of ``GRAMMAR_VARIANTS``.
    """
    return tuple(
        Variant(
            name=entry.name,
            hypothesis=entry.hypothesis,
            kind=entry.kind,
            note=entry.note,
            encode=grammar_encoder(baselines, entry.grammar),
            needs_seeds=False,
        )
        for entry in GRAMMAR_VARIANTS
    )
