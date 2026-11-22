import itertools
from dataclasses import dataclass
from typing import Final, List, Mapping, Optional, Sequence, Tuple

from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.enums import SpectrumMethod

from .config.level import WorkingLevel
from .config.settings import Overrides, overridden
from .levels import level_config

LABEL_SEPARATOR: Final[str] = "-"
EXPONENT_TAG: Final[str] = "pe"
TEMPORAL_WEIGHT_TAG: Final[str] = "tw"
WHOLE_BLEND: Final[float] = 1.0


@dataclass(frozen=True)
class CalibrationVariant:
    """One configuration a run measures, and the level it matches the sounds at.

    Attributes:
        label: The name its rows and renders carry, spelling out what it departs from the base by.
        config: The configuration the sounds are converted under.
        level: The level the sounds are matched at.
    """

    label: str
    config: Config
    level: WorkingLevel


def build_variants(
    base: Config,
    methods: List[SpectrumMethod],
    perceptual_exponents: List[float],
    temporal_weights: List[float],
    *,
    settings: Mapping[str, Overrides],
    levels: Sequence[WorkingLevel],
) -> List[CalibrationVariant]:
    """
    The variants a run measures: every point of its sweep over a base configuration.

    The sweep is the product of the spectrum methods, the perceptual exponents, the temporal weights,
    the named sets of settings and the levels, in that order, so the last of them varies fastest.
    Each point keeps the base and overrides the method, the exponent and (when swept) the temporal
    weight. The base is measured first, and every named set after it, written over it, so a set is
    read against the configuration it departs from. Every level is measured beside the others. The
    label spells each overridden value, the set's name and a level other than the default, so a
    report row stays self-describing.

    Args:
        base: Configuration providing every value the sweep leaves untouched.
        methods: Spectrum methods to evaluate.
        perceptual_exponents: Values of `metric.perceptual_exponent` to evaluate.
        temporal_weights: Values of `weights.temporal_loss_weight` to evaluate;
            an empty list keeps the base blend.
        settings: Named sets of settings to measure beside the base, by name.
        levels: The levels the sounds are matched at.

    Returns:
        One labeled variant per point of the sweep.

    Raises:
        ValidationError: If a set of settings names a setting the configuration lacks.
    """
    swept_temporal: List[Optional[float]] = list(temporal_weights) if temporal_weights else [None]
    swept_settings: List[Optional[str]] = [None, *settings]
    variants: List[CalibrationVariant] = []
    for method, exponent, temporal_weight, name, level in itertools.product(
        methods, perceptual_exponents, swept_temporal, swept_settings, levels
    ):
        label, config = _criterion_point(base, method, exponent, temporal_weight)
        if name is not None:
            label, config = _labeled(label, name), overridden(config, settings[name])

        variants.append(_at_level(label, config, level))

    return variants


def _criterion_point(
    base: Config,
    method: SpectrumMethod,
    exponent: float,
    temporal_weight: Optional[float],
) -> Tuple[str, Config]:
    """The label and configuration of one point of the method and criterion sweep.

    The point reads the library under ``method`` and scores at ``exponent``. A swept temporal weight
    sets the blend of the criterion, and with none swept the base blend stays.
    """
    label = f"{method.value}{LABEL_SEPARATOR}{EXPONENT_TAG}{exponent:g}"
    generation = base.generation.model_copy(
        update={
            "metric": base.generation.metric.model_copy(update={"perceptual_exponent": exponent}),
        }
    )
    if temporal_weight is not None:
        label = _labeled(label, f"{TEMPORAL_WEIGHT_TAG}{temporal_weight:g}")
        generation = _blended(generation, temporal_weight)

    config = base.model_copy(
        update={
            "library": base.library.model_copy(update={"spectrum_method": method}),
            "generation": generation,
        }
    )
    return label, config


def _blended(generation: GenerationConfig, temporal_weight: float) -> GenerationConfig:
    """The generation blending its losses as ``temporal_weight`` sets: that share temporal, the rest spectral."""
    weights = generation.weights.model_copy(
        update={
            "temporal_loss_weight": temporal_weight,
            "spectral_loss_weight": WHOLE_BLEND - temporal_weight,
        }
    )
    return generation.model_copy(update={"weights": weights})


def _at_level(label: str, config: Config, level: WorkingLevel) -> CalibrationVariant:
    """The variant converting at ``level``, a level other than the default ending its label."""
    if level != WorkingLevel.DEFAULT:
        label = _labeled(label, level.value)

    return CalibrationVariant(label=label, config=level_config(config, level), level=level)


def _labeled(label: str, part: str) -> str:
    """The label with ``part`` joined to its end, a part per departure from the base."""
    return f"{label}{LABEL_SEPARATOR}{part}"
