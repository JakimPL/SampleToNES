from typing import Dict, Final, Sequence, Tuple

from codec_study.variants.production import BASELINE
from codec_study.variants.variant import Variant

VARIANTS: Final[Dict[str, Variant]] = {BASELINE.name: BASELINE}


def selected_variants(names: Sequence[str]) -> Tuple[Variant, ...]:
    """The variants a run encodes every song under, the baseline always first.

    Args:
        names: The names the run asks for.

    Returns:
        Tuple[Variant, ...]: The baseline, then the named variants in the order given.

    Raises:
        KeyError: If a name is registered to no variant.
    """
    unknown = [name for name in names if name not in VARIANTS]
    if unknown:
        raise KeyError(f"no variant is called {', '.join(unknown)}; the registry holds {', '.join(VARIANTS)}")

    chosen = [VARIANTS[name] for name in names if name != BASELINE.name]
    return (BASELINE, *chosen)
