from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Mapping, Optional, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.headless.library import generate_library
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibrary
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_shared.logger import logger

from .corpus.item import CorpusItem
from .referee.protocol import Judgment, Referee
from .renders import RenderRecord, sounding_timelines, write_channel_renders, write_recording, write_render


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
    component: str
    score: float


def build_variants(
    base: Config,
    methods: List[SpectrumMethod],
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
                label = f"{method.value}-pe{exponent:g}"
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
                variants.append(
                    CalibrationVariant(
                        label=label,
                        config=config,
                    )
                )

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
    run_directory: Path,
    channels: FrozenSet[ChannelName],
) -> List[CalibrationRow]:
    """
    Reconstruct the corpus under every variant, score the results and keep what was heard.

    Each corpus item is reconstructed with the variant's configuration and every
    referee judges the approximation against the preprocessed original, both on the
    common scale set by the working-level coefficient. The render, the recording it
    reconstructs and a record of the scores and the sounding frames are written under
    the run directory, so a render can be heard and read again after the run.

    Args:
        variants: Labeled configurations to evaluate.
        items: Corpus items, carrying the category used in reports.
        item_paths: Written WAV path per corpus item name.
        referees: Referees scoring each reconstruction.
        run_directory: The directory the run writes its renders and recordings into.
        channels: The channels every variant reconstructs with.

    Returns:
        One row per (variant, item, referee, reading).
    """
    rows: List[CalibrationRow] = []
    for variant in variants:
        ensure_library(variant.config)
        reconstructor = Reconstructor(variant.config, channels)
        sample_rate = variant.config.library.sample_rate
        for position, item in enumerate(items):
            path = item_paths[item.name]
            reconstruction = reconstructor(path)
            if reconstruction is None:
                logger.info(f"[{variant.label}] {item.name}: reconstruction unavailable")
                continue

            reference, estimate = _compared_signals(reconstructor.load_audio(path), reconstruction)
            judgments = {referee.name: referee.judge(reference, estimate) for referee in referees}
            silence = {referee.name: referee.judge(reference, np.zeros_like(reference)).score for referee in referees}
            rows.extend(_rows(variant, item, judgments))

            write_recording(run_directory, item.name, reference * reconstruction.coefficient, sample_rate)
            write_render(
                run_directory,
                RenderRecord(
                    variant=variant.label,
                    item=item.name,
                    position=position,
                    category=item.category,
                    timelines=sounding_timelines(_played_instructions(reconstruction)),
                    judgments={name: judgment.readings() for name, judgment in judgments.items()},
                    silence=silence,
                ),
                estimate * reconstruction.coefficient,
                sample_rate,
            )
            write_channel_renders(
                run_directory,
                variant.label,
                item.name,
                _channel_audio(reconstruction, estimate.shape[0]),
                sample_rate,
            )
            logger.info(f"[{variant.label}] {item.name}: scored")

    return rows


def _compared_signals(
    recording: np.ndarray,
    reconstruction: Reconstruction,
) -> Tuple[np.ndarray, np.ndarray]:
    """The recording and its approximation on the working-level scale, cut to a common length."""
    reference = recording / reconstruction.coefficient
    estimate = np.asarray(reconstruction.approximation, dtype=np.float64)
    length = min(reference.shape[0], estimate.shape[0])
    return reference[:length], estimate[:length]


def _channel_audio(reconstruction: Reconstruction, length: int) -> Dict[ChannelName, np.ndarray]:
    """What each sounding channel contributes to the render, on the recording's scale and length."""
    approximations = reconstruction.approximations
    return {
        channel_name: approximations[channel_name][:length] * reconstruction.coefficient
        for channel_name in reconstruction.playing_channels
        if channel_name in approximations
    }


def _played_instructions(reconstruction: Reconstruction) -> Dict[ChannelName, List[InstructionUnion]]:
    instructions = reconstruction.instructions
    return {channel_name: instructions[channel_name] for channel_name in reconstruction.playing_channels}


def _rows(
    variant: CalibrationVariant,
    item: CorpusItem,
    judgments: Mapping[str, Judgment],
) -> List[CalibrationRow]:
    return [
        CalibrationRow(
            variant=variant.label,
            item=item.name,
            category=item.category,
            referee=referee,
            component=component,
            score=value,
        )
        for referee, judgment in judgments.items()
        for component, value in judgment.readings().items()
    ]
