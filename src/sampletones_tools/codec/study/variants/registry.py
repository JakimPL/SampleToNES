from typing import Dict, Final, Sequence, Tuple

from sampletones_tools.codec.study.variants.baselines import Baselines, baseline_variant
from sampletones_tools.codec.study.variants.layouts import LAYOUT_VARIANTS
from sampletones_tools.codec.study.variants.packing import COMBINED_VARIANTS, PACKING_VARIANTS
from sampletones_tools.codec.study.variants.production import BASELINE_NAME, BUDGET_VARIANTS, SEED_VARIANTS
from sampletones_tools.codec.study.variants.sandbox import grammar_variants
from sampletones_tools.codec.study.variants.variant import Variant

EVERY_VARIANT: Final[str] = "all"


def variants(baselines: Baselines) -> Dict[str, Variant]:
    """Every variant a run may encode under, by name, the baseline first.

    Args:
        baselines: Where the production encodings are kept for the variants built on them.

    Returns:
        Dict[str, Variant]: The variants, in the order a run encodes them.
    """
    every = (
        baseline_variant(baselines),
        *SEED_VARIANTS,
        *BUDGET_VARIANTS,
        *grammar_variants(baselines),
        *LAYOUT_VARIANTS,
        *PACKING_VARIANTS,
        *COMBINED_VARIANTS,
    )
    return {variant.name: variant for variant in every}


def selected_variants(
    names: Sequence[str],
    baselines: Baselines,
) -> Tuple[Variant, ...]:
    """The variants a run encodes every song under, the baseline always first.

    Args:
        names: The names the run asks for, or ``all`` for every registered variant.
        baselines: Where the production encodings are kept for the variants built on them.

    Returns:
        Tuple[Variant, ...]: The baseline, then the named variants in the order given.

    Raises:
        ValueError: If a name is registered to no variant.
    """
    registered = variants(baselines)
    if EVERY_VARIANT in names:
        return tuple(registered.values())

    unknown = [name for name in names if name not in registered]
    if unknown:
        raise ValueError(
            f"No variant is called {', '.join(unknown)}; the variants are {', '.join(registered)} or {EVERY_VARIANT}."
        )

    chosen = [registered[name] for name in names if name != BASELINE_NAME]
    return (registered[BASELINE_NAME], *chosen)
