from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.library import InstructionLibrary
from sampletones_core.reconstructions import Reconstructor
from sampletones_core.scripts.library import generate_library
from sampletones_shared.logger import logger

from .corpus import CorpusItem
from .referee import Referee


@dataclass(frozen=True)
class CalibrationVariant:
    label: str
    config: Config


@dataclass(frozen=True)
class CalibrationRow:
    variant: str
    item: str
    category: str
    referee: str
    score: float


def build_variants(
    base: Config,
    methods: List[str],
    perceptual_exponents: List[float],
    temporal_weights: List[float],
) -> List[CalibrationVariant]:
    """
    Cartesian sweep of spectrum methods and criterion knobs over a base configuration.

    Each variant keeps the base configuration and overrides the spectrum method, the
    perceptual exponent, and (when swept) the temporal loss weight; the label encodes
    the overridden values so report rows stay self-describing.

    Args:
        base: Configuration providing every value the sweep leaves untouched.
        methods: Spectrum methods to evaluate.
        perceptual_exponents: Values of `metric.perceptual_exponent` to evaluate.
        temporal_weights: Values of `weights.temporal_loss_weight` to evaluate;
            an empty list keeps the base blend.

    Returns:
        One labeled variant per sweep combination.
    """
    variants: List[CalibrationVariant] = []
    swept_temporal: List[Optional[float]] = list(temporal_weights) if temporal_weights else [None]

    for method in methods:
        for exponent in perceptual_exponents:
            for temporal_weight in swept_temporal:
                label = f"{method}-pe{exponent:g}"
                generation = base.generation.model_copy(
                    update={
                        "metric": base.generation.metric.model_copy(update={"perceptual_exponent": exponent}),
                    }
                )
                if temporal_weight is not None:
                    label = f"{label}-tw{temporal_weight:g}"
                    generation = generation.model_copy(
                        update={
                            "weights": generation.weights.model_copy(
                                update={
                                    "temporal_loss_weight": temporal_weight,
                                    "spectral_loss_weight": 1.0 - temporal_weight,
                                }
                            )
                        }
                    )

                config = base.model_copy(
                    update={
                        "library": base.library.model_copy(update={"spectrum_method": method}),
                        "generation": generation,
                    }
                )
                variants.append(CalibrationVariant(label=label, config=config))

    return variants


def ensure_library(config: Config) -> None:
    """
    Generate the instruction library of a configuration when it is absent.

    Args:
        config: Configuration whose library must exist before reconstruction.
    """
    window = Window.from_config(config)
    library = InstructionLibrary.from_config(config)
    key = library.create_key(config, window)
    path = library.get_path(key)
    if path.exists():
        return

    logger.info(f"Generating missing library: {path.name}")
    generate_library(config)


def evaluate_variants(
    variants: List[CalibrationVariant],
    items: List[CorpusItem],
    item_paths: Dict[str, Path],
    referees: List[Referee],
) -> List[CalibrationRow]:
    """
    Reconstruct the corpus under every variant and score the results.

    Each corpus item is reconstructed with the variant's configuration and every
    referee scores the approximation against the preprocessed original, both on the
    common scale set by the working-level coefficient.

    Args:
        variants: Labeled configurations to evaluate.
        items: Corpus items, carrying the category used in reports.
        item_paths: Written WAV path per corpus item name.
        referees: Referees scoring each reconstruction.

    Returns:
        One row per (variant, item, referee).
    """
    rows: List[CalibrationRow] = []
    for variant in variants:
        ensure_library(variant.config)
        reconstructor = Reconstructor(variant.config)
        for item in items:
            path = item_paths[item.name]
            reconstruction = reconstructor(path)
            if reconstruction is None:
                logger.info(f"[{variant.label}] {item.name}: reconstruction unavailable")
                continue

            reference = reconstructor.load_audio(path) / reconstruction.coefficient
            estimate = np.asarray(reconstruction.approximation, dtype=np.float64)
            length = min(reference.shape[0], estimate.shape[0])

            for referee in referees:
                score = referee.score(reference[:length], estimate[:length])
                rows.append(
                    CalibrationRow(
                        variant=variant.label,
                        item=item.name,
                        category=item.category,
                        referee=referee.name,
                        score=score,
                    )
                )

            logger.info(f"[{variant.label}] {item.name}: scored")

    return rows
