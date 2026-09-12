from typing import Dict, Final, Sequence, Tuple

from codec_study.variants.production import BASELINE, BUDGET_VARIANTS, SEED_VARIANTS
from codec_study.variants.variant import Variant

EVERY_VARIANT: Final[str] = "all"
VARIANTS: Final[Dict[str, Variant]] = {
    variant.name: variant for variant in (BASELINE, *SEED_VARIANTS, *BUDGET_VARIANTS)
}


def selected_variants(names: Sequence[str]) -> Tuple[Variant, ...]:
    """The variants a run encodes every song under, the baseline always first.

    Args:
        names: The names the run asks for, or ``all`` for every registered variant.

    Returns:
        Tuple[Variant, ...]: The baseline, then the named variants in the order given.

    Raises:
        KeyError: If a name is registered to no variant.
    """
    if EVERY_VARIANT in names:
        return tuple(VARIANTS.values())

    unknown = [name for name in names if name not in VARIANTS]
    if unknown:
        raise KeyError(f"no variant is called {', '.join(unknown)}; the registry holds {', '.join(VARIANTS)}")

    chosen = [VARIANTS[name] for name in names if name != BASELINE.name]
    return (BASELINE, *chosen)
