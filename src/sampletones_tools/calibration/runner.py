from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.logger import logger

from .corpus.item import CorpusItem
from .referee.panel import RefereePanel
from .referee.protocol import Judgment
from .renders import (
    RenderRecord,
    sounding_timelines,
    write_channel_renders,
    write_record,
    write_recording,
    write_render,
)


@dataclass(frozen=True)
class CalibrationVariant:
    label: str
    config: Config


@dataclass(frozen=True)
class CalibrationRow:
    variant: str
    item: str
    family: str
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


@dataclass(frozen=True)
class Conversion:
    """One reference sound a run converts under one variant, and where its record goes.

    Attributes:
        variant: The configuration the sound is converted under.
        item: The reference sound.
        position: The sound's place in the corpus, which its record keeps.
        paths: The written files the conversion reads, one per stem of a sound held as stems.
        stems: The stems setup the files are converted under, or ``None`` for one recording.
        channels: The channels the conversion covers.
        run_directory: The directory the run writes its renders and recordings into.
    """

    variant: CalibrationVariant
    item: CorpusItem
    position: int
    paths: Tuple[Path, ...]
    stems: Optional[StemsConfig]
    channels: FrozenSet[ChannelName]
    run_directory: Path


def evaluate_conversion(
    conversion: Conversion,
    reconstructor: Reconstructor,
    panel: RefereePanel,
) -> List[CalibrationRow]:
    """
    Reconstruct one sound, score it, and keep what was heard.

    The sound is reconstructed with the variant's configuration and every referee judges the
    approximation against the preprocessed original, both on the common scale set by the
    working-level coefficient. A sound whose truth the corpus knows is also read against it by
    every truth referee, and every conversion is read on its own by the conversion referees. A
    sound held as stems is converted under its setup. A listed sound's render, recording and channel
    parts are written under the
    run directory, and every sound's record comes last, so a record stands only for a conversion
    written whole.

    Args:
        conversion: The sound, the variant and where the record goes.
        reconstructor: The variant's reconstructor over the conversion's channels.
        panel: The referees judging the reconstruction.

    Returns:
        One row per (referee, reading), empty where the reconstruction is unavailable.
    """
    variant, item = conversion.variant, conversion.item
    reconstruction = (
        reconstructor.reconstruct(list(conversion.paths), conversion.stems)
        if conversion.stems is not None
        else reconstructor(conversion.paths[0])
    )
    if reconstruction is None:
        logger.info(f"[{variant.label}] {item.name}: reconstruction unavailable")
        return []

    reference, estimate = _compared_signals(reconstructor.load_audio(list(conversion.paths)), reconstruction)
    judgments = _judgments(item, reference, estimate, reconstruction, panel)
    silence = {referee.name: referee.judge(reference, np.zeros_like(reference)).score for referee in panel.audio}
    record = RenderRecord(
        variant=variant.label,
        item=item.name,
        position=conversion.position,
        family=item.family.value,
        category=item.category,
        listed=item.listed,
        timelines=sounding_timelines(_played_instructions(reconstruction)),
        judgments={name: judgment.readings() for name, judgment in judgments.items()},
        silence=silence,
    )
    sample_rate = variant.config.library.sample_rate
    if item.listed:
        _write_listened(conversion.run_directory, record, reference, estimate, reconstruction, sample_rate)
    else:
        write_record(conversion.run_directory, record)

    logger.debug(f"[{variant.label}] {item.name}: scored")
    return recorded_rows(record)


def recorded_rows(record: RenderRecord) -> List[CalibrationRow]:
    """The rows a record holds, one per (referee, reading), as the conversion that wrote it scored them."""
    return [
        CalibrationRow(
            variant=record.variant,
            item=record.item,
            family=record.family,
            category=record.category,
            referee=referee,
            component=component,
            score=value,
        )
        for referee, readings in record.judgments.items()
        for component, value in readings.items()
    ]


def _write_listened(
    run_directory: Path,
    record: RenderRecord,
    reference: np.ndarray,
    estimate: np.ndarray,
    reconstruction: Reconstruction,
    sample_rate: int,
) -> None:
    """Write what the page plays of a listed item: the recording, the channel parts, then the render and its record."""
    write_recording(run_directory, record.item, reference * reconstruction.coefficient, sample_rate)
    write_channel_renders(
        run_directory,
        record.variant,
        record.item,
        _channel_audio(reconstruction, estimate.shape[0]),
        sample_rate,
    )
    write_render(run_directory, record, estimate * reconstruction.coefficient, sample_rate)


def _judgments(
    item: CorpusItem,
    reference: np.ndarray,
    estimate: np.ndarray,
    reconstruction: Reconstruction,
    panel: RefereePanel,
) -> Dict[str, Judgment]:
    """Every referee's judgment of a render, the audio referees first so a report leads with them."""
    judgments = {referee.name: referee.judge(reference, estimate) for referee in panel.audio}
    truth = item.truth
    if truth is not None:
        for referee in panel.truth:
            judged = referee.judge(truth, reconstruction)
            if judged is not None:
                judgments[referee.name] = judged

    for conversion_referee in panel.conversion:
        judged = conversion_referee.judge(reconstruction)
        if judged is not None:
            judgments[conversion_referee.name] = judged

    return judgments


def _compared_signals(
    recording: np.ndarray,
    reconstruction: Reconstruction,
) -> Tuple[np.ndarray, np.ndarray]:
    """The recording and its approximation on the working-level scale, cut to a common length."""
    reference = recording / reconstruction.coefficient
    estimate = np.asarray(rendered_mix(reconstruction), dtype=np.float64)
    length = min(reference.shape[0], estimate.shape[0])
    return reference[:length], estimate[:length]


def _channel_audio(reconstruction: Reconstruction, length: int) -> Dict[ChannelName, np.ndarray]:
    """What each sounding channel contributes to the render, on the recording's scale and length."""
    approximations = rendered_channels(reconstruction)
    return {
        channel_name: approximations[channel_name][:length] * reconstruction.coefficient
        for channel_name in reconstruction.playing_channels
        if channel_name in approximations
    }


def _played_instructions(reconstruction: Reconstruction) -> Dict[ChannelName, List[InstructionUnion]]:
    instructions = reconstruction.instructions
    return {channel_name: instructions[channel_name] for channel_name in reconstruction.playing_channels}
