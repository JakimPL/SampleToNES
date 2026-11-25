from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
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
from .rows import CalibrationRow, recorded_rows
from .trace import SearchTrace, TraceRecorder
from .variants import CalibrationVariant


@dataclass(frozen=True)
class Conversion:
    """One reference sound a run converts under one variant, and where its record goes.

    A sound held as stems converts under its stems setup, and a sound naming channels of its own
    converts over them. Every other sound converts as one recording over the run's channels.

    Attributes:
        variant: The configuration the sound is converted under.
        item: The reference sound.
        position: The sound's place in the corpus, which its record keeps.
        paths: The written files the conversion reads, one per stem of a sound held as stems.
        run_channels: The channels the run converts a sound over where the sound names none.
        run_directory: The directory the run writes its renders and recordings into.
    """

    variant: CalibrationVariant
    item: CorpusItem
    position: int
    paths: Tuple[Path, ...]
    run_channels: FrozenSet[ChannelName]
    run_directory: Path

    @property
    def stems(self) -> Optional[StemsConfig]:
        """The stems setup the files are converted under, or ``None`` for one recording."""
        return self.item.stems.config if self.item.stems is not None else None

    @property
    def channels(self) -> FrozenSet[ChannelName]:
        """The channels the conversion covers: the sound's own where it names them, else the run's."""
        return self.item.channels if self.item.channels is not None else self.run_channels

    def reconstruct(self, reconstructor: Reconstructor, recorder: TraceRecorder) -> Optional[Reconstruction]:
        """The sound reconstructed under its stems setup or as one recording, ``recorder`` watching the search."""
        if self.stems is not None:
            return reconstructor.reconstruct(list(self.paths), self.stems, observe=recorder)

        return reconstructor(self.paths[0], observe=recorder)


def evaluate_conversion(
    conversion: Conversion,
    reconstructor: Reconstructor,
    panel: RefereePanel,
) -> List[CalibrationRow]:
    """
    Reconstruct one sound, judge it, and keep what was heard.

    The recording and the render are judged on the common scale the working-level coefficient
    sets. The record is written last, after the audio of a listed sound, so a record stands only for a
    conversion written whole, and a resumed run takes it up as done.

    Args:
        conversion: The sound, the variant and where the record goes.
        reconstructor: The variant's reconstructor over the conversion's channels.
        panel: The referees judging the reconstruction.

    Returns:
        One row per (referee, reading), read from the record written, empty where the reconstruction
        is unavailable.
    """
    variant, item = conversion.variant, conversion.item
    recorder = TraceRecorder()
    reconstruction = conversion.reconstruct(reconstructor, recorder)
    if reconstruction is None:
        logger.info(f"[{variant.label}] {item.name}: reconstruction unavailable")
        return []

    reference, estimate = _compared_signals(reconstructor.load_audio(list(conversion.paths)), reconstruction)
    judgments = _judgments(item, reference, estimate, reconstruction, recorder.trace, panel)
    record = _record(conversion, reconstruction, judgments, _silence_scores(reference, panel))
    if item.listed:
        _write_listened(conversion.run_directory, record, reference, estimate, reconstruction, variant)
    else:
        write_record(conversion.run_directory, record)

    logger.debug(f"[{variant.label}] {item.name}: scored")
    return recorded_rows(record)


def _judgments(
    item: CorpusItem,
    reference: np.ndarray,
    estimate: np.ndarray,
    reconstruction: Reconstruction,
    trace: Optional[SearchTrace],
    panel: RefereePanel,
) -> Dict[str, Judgment]:
    """Every referee's judgment of a render, in the order the record keeps and the report reads them.

    The audio referees lead, so the first of them heads the report and the page. A sound whose truth
    the corpus knows is read against it by every truth referee, and its search by every trace
    referee. Every conversion is read on its own by the conversion referees. A referee with no
    reading of the conversion is left out.
    """
    judgments = {referee.name: referee.judge(reference, estimate) for referee in panel.audio}
    truth = item.truth
    if truth is not None:
        for referee in panel.truth:
            judged = referee.judge(truth, reconstruction)
            if judged is not None:
                judgments[referee.name] = judged

        if trace is not None:
            for trace_referee in panel.trace:
                traced = trace_referee.judge(truth, trace, reconstruction)
                if traced is not None:
                    judgments[trace_referee.name] = traced

    for conversion_referee in panel.conversion:
        judged = conversion_referee.judge(reconstruction)
        if judged is not None:
            judgments[conversion_referee.name] = judged

    return judgments


def _silence_scores(reference: np.ndarray, panel: RefereePanel) -> Dict[str, float]:
    """Every audio referee's score for complete silence against the recording, the distance a render closes."""
    return {referee.name: referee.judge(reference, np.zeros_like(reference)).score for referee in panel.audio}


def _record(
    conversion: Conversion,
    reconstruction: Reconstruction,
    judgments: Dict[str, Judgment],
    silence: Dict[str, float],
) -> RenderRecord:
    """The record of what the conversion heard: its level, its readings, silence's scores and each channel's frames."""
    item = conversion.item
    return RenderRecord(
        variant=conversion.variant.label,
        item=item.name,
        position=conversion.position,
        family=item.family.value,
        category=item.category,
        listed=item.listed,
        level=conversion.variant.level,
        timelines=sounding_timelines(_played_instructions(reconstruction)),
        judgments={name: judgment.readings() for name, judgment in judgments.items()},
        silence=silence,
    )


def _write_listened(
    run_directory: Path,
    record: RenderRecord,
    reference: np.ndarray,
    estimate: np.ndarray,
    reconstruction: Reconstruction,
    variant: CalibrationVariant,
) -> None:
    """Write what the page plays of a listed sound: the recording, the channel parts, then the render and its record.

    Each file is written back on the recording's own scale, and the recording is kept at the level the
    render was matched at, so the page plays a render at the level of the recording it reconstructs.
    """
    sample_rate = variant.config.library.sample_rate
    write_recording(run_directory, record.level, record.item, reference * reconstruction.coefficient, sample_rate)
    write_channel_renders(
        run_directory,
        record.variant,
        record.item,
        _channel_audio(reconstruction, estimate.shape[0]),
        sample_rate,
    )
    write_render(run_directory, record, estimate * reconstruction.coefficient, sample_rate)


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
    """The instructions of every channel the reconstruction plays."""
    instructions = reconstruction.instructions
    return {channel_name: instructions[channel_name] for channel_name in reconstruction.playing_channels}
