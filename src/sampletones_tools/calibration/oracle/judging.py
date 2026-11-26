import zlib
from pathlib import Path
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from tqdm import tqdm

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.layout import ORACLE_LABEL
from sampletones_tools.calibration.referee.panel import RefereePanel
from sampletones_tools.calibration.referee.protocol import Judgment
from sampletones_tools.calibration.renders import (
    RenderRecord,
    read_record,
    sounding_timelines,
    write_channel_renders,
    write_record,
    write_recording,
    write_render,
)
from sampletones_tools.calibration.rows import CalibrationRow, recorded_rows

from .reading import OracleReading
from .starts import started_channels

ORACLE_STARTS: Final[int] = 8
ORACLE_SEED: Final[int] = 0
PROGRESS_LABEL: Final[str] = "Oracle"
PROGRESS_UNIT: Final[str] = "sound"

StartedRender = Tuple[Dict[ChannelName, np.ndarray], np.ndarray]


def oracle_rows(
    items: Sequence[CorpusItem],
    panel: RefereePanel,
    run_directory: Path,
    config: Config,
    *,
    resume: bool,
) -> List[CalibrationRow]:
    """The oracle's rows of every sound written as NES frames: what playing its frames exactly scores.

    A sound written as frames carries them as its truth, and its recording is what they render to
    from the channels' reset states. A conversion naming every frame right still plays the noise's
    sequence from wherever its own earlier frames left it, so the oracle renders the frames from
    ``ORACLE_STARTS`` starting states of the noise (``started_channels``) and reads every audio
    referee over them (``OracleReading``). It stands beside the variants as the best a transcription
    can score. A resumed run takes the record a sound's oracle left.

    Args:
        items: The run's reference sounds, in corpus order.
        panel: The referees, whose audio referees judge each render.
        run_directory: The directory the run writes its renders and records into.
        config: The configuration the corpus renders its frames at.
        resume: Whether a sound's oracle that left a record is taken from it.

    Returns:
        One row per (sound, referee, reading), in corpus order.
    """
    written = [(position, item) for position, item in enumerate(items) if _written_frames(item) is not None]
    rows: List[CalibrationRow] = []
    for position, item in tqdm(written, desc=PROGRESS_LABEL, unit=PROGRESS_UNIT):
        record = read_record(run_directory, ORACLE_LABEL, item.name) if resume else None
        if record is None:
            record = judge_oracle(item, position, panel, run_directory, config)

        rows.extend(recorded_rows(record))

    return rows


def judge_oracle(
    item: CorpusItem,
    position: int,
    panel: RefereePanel,
    run_directory: Path,
    config: Config,
) -> RenderRecord:
    """Render a written sound's frames from every start, judge each against the sound, and write the record.

    Each sound draws its starts from a seed of its own name, so a sound's oracle reads alike in
    every run that holds it. The render is judged against the sound as its file holds it, the true
    level, so the oracle reads the frames alone. A listed sound's recording and the typical start's
    render are written for the page (``OracleReading.typical``).

    Args:
        item: A sound written as NES frames.
        position: The sound's place in the corpus.
        panel: The referees, whose audio referees judge each render.
        run_directory: The directory the run writes its renders and records into.
        config: The configuration the corpus renders its frames at.

    Returns:
        The oracle's record of the sound.

    Raises:
        ValueError: If the sound is not written as NES frames.
    """
    instructions = _written_frames(item)
    if instructions is None:
        raise ValueError(f"Sound '{item.name}' is not written as NES frames")

    audio = np.asarray(item.audio, dtype=np.float64)
    random = np.random.default_rng([ORACLE_SEED, zlib.crc32(item.name.encode())])
    renders = [_render(instructions, config, random, audio.shape[0]) for _ in range(ORACLE_STARTS)]
    reading = OracleReading(starts=tuple(_judged(panel, audio, mixed) for _, mixed in renders))
    record = RenderRecord(
        variant=ORACLE_LABEL,
        item=item.name,
        position=position,
        family=item.family.value,
        category=item.category,
        listed=item.listed,
        level=VariantLevel.TRUE,
        timelines=sounding_timelines({channel: instructions[channel] for channel in renders[0][0]}),
        judgments=reading.readings(),
        silence={referee.name: referee.judge(audio, np.zeros_like(audio)).score for referee in panel.audio},
    )
    if item.listed:
        headline = panel.audio[0].name
        channels, mixed = renders[reading.typical(headline)]
        _write_listened(run_directory, record, audio, channels, mixed, config.library.sample_rate)
    else:
        write_record(run_directory, record)

    return record


def _written_frames(item: CorpusItem) -> Optional[Mapping[ChannelName, Sequence[InstructionUnion]]]:
    """The frames a sound written as NES frames plays, which its truth holds; ``None`` for a sound written otherwise."""
    if item.truth is None or not item.truth.instructions:
        return None

    return item.truth.instructions


def _render(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    config: Config,
    random: np.random.Generator,
    length: int,
) -> StartedRender:
    """Each sounding channel's frames from one drawn start, and their mix, cut to the sound's ``length``.

    A sound none of whose channels sounds mixes to its length of silence.
    """
    channels = {channel: audio[:length] for channel, audio in started_channels(instructions, config, random).items()}
    if not channels:
        return channels, np.zeros(length)

    return channels, np.asarray(mix(list(channels.values())), dtype=np.float64)


def _judged(panel: RefereePanel, audio: np.ndarray, mixed: np.ndarray) -> Dict[str, Judgment]:
    """Every audio referee's judgment of one render against the sound, over the length they share."""
    length = min(audio.shape[0], mixed.shape[0])
    return {referee.name: referee.judge(audio[:length], mixed[:length]) for referee in panel.audio}


def _write_listened(
    run_directory: Path,
    record: RenderRecord,
    audio: np.ndarray,
    channels: Mapping[ChannelName, np.ndarray],
    mixed: np.ndarray,
    sample_rate: int,
) -> None:
    """Write what the page plays of the oracle: the sound at the true level, the start's channel parts, its render."""
    write_recording(run_directory, record.level, record.item, audio, sample_rate)
    write_channel_renders(run_directory, record.variant, record.item, channels, sample_rate)
    write_render(run_directory, record, mixed, sample_rate)
