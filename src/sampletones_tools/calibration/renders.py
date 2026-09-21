from itertools import combinations
from pathlib import Path
from typing import Dict, Final, List, Mapping, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.audio.io import write_flac
from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.paths.extensions import EXT_FILE_FLAC, EXT_FILE_JSON
from sampletones_shared.utils.system.paths import get_filename

from .layout import RECORDINGS_DIRECTORY, RENDERS_DIRECTORY, combination_name

SOUNDING_FRAME: Final[str] = "1"
RESTING_FRAME: Final[str] = "0"


class RenderRecord(BaseModel):
    """
    What a calibration run heard in one render: the scores it drew and which channel sounded when.

    A record sits beside its render's audio file, so a run can be studied after it ends from what it
    wrote.

    Attributes:
        variant: The label of the configuration the render comes from.
        item: The corpus item rendered.
        position: The item's place in the corpus.
        category: The item's corpus category.
        timelines: One character per frame for each channel, ``SOUNDING_FRAME`` where it sounds.
        judgments: Every referee's readings of the render, by referee name.
        silence: Every referee's score for complete silence against the same recording.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str
    item: str
    position: int
    category: str
    timelines: Dict[str, str]
    judgments: Dict[str, Dict[str, float]]
    silence: Dict[str, float]


def sounding_timelines(instructions: Mapping[ChannelName, Sequence[InstructionUnion]]) -> Dict[str, str]:
    """Each channel's frames as characters, ``SOUNDING_FRAME`` where its instruction is on."""
    return {
        channel_name.value: "".join(SOUNDING_FRAME if instruction.on else RESTING_FRAME for instruction in stream)
        for channel_name, stream in instructions.items()
    }


def channel_subsets(channels: Sequence[ChannelName]) -> List[Tuple[ChannelName, ...]]:
    """Every part of the channels a render sounds, from one channel up to all but one.

    A page switching a channel on or off plays a file rather than mixing in the browser, so each
    part a listener may ask for is written once and heard exactly as the run made it.
    """
    return [subset for size in range(1, len(channels)) for subset in combinations(channels, size)]


def write_render(
    run_directory: Path,
    record: RenderRecord,
    audio: np.ndarray,
    sample_rate: int,
) -> None:
    """
    Write a render's audio and its record under the run's renders, in a directory per variant.

    Args:
        run_directory: The directory the calibration run writes into.
        record: What the run heard in the render.
        audio: The render on the scale of the recording it reconstructs.
        sample_rate: Sampling rate of the render in Hz.
    """
    directory = variant_directory(run_directory, record.variant)
    directory.mkdir(parents=True, exist_ok=True)
    write_flac(directory / get_filename(record.item, EXT_FILE_FLAC), sample_rate, audio.astype(np.float32))
    (directory / get_filename(record.item, EXT_FILE_JSON)).write_text(
        record.model_dump_json(indent=1), encoding="utf-8"
    )


def write_channel_renders(
    run_directory: Path,
    variant: str,
    item: str,
    approximations: Mapping[ChannelName, np.ndarray],
    sample_rate: int,
) -> List[Tuple[ChannelName, ...]]:
    """
    Write one clip per part of the channels a render sounds, in a directory named after the item.

    The parts are mixed from the same per-channel audio the whole render is mixed from, so a part
    and the whole stand sample for sample and a listener switching between them hears one decision.

    Args:
        run_directory: The directory the calibration run writes into.
        variant: The label of the configuration the render comes from.
        item: The corpus item rendered.
        approximations: The audio each sounding channel contributes, on the render's own scale.
        sample_rate: Sampling rate of the render in Hz.

    Returns:
        The parts written, each a tuple of channels in the order the render sounds them.
    """
    channels = tuple(approximations)
    subsets = channel_subsets(channels)
    if not subsets:
        return []

    directory = item_directory(run_directory, variant, item)
    directory.mkdir(parents=True, exist_ok=True)
    for subset in subsets:
        audio = mix([approximations[channel] for channel in subset])
        path = directory / get_filename(combination_name(subset), EXT_FILE_FLAC)
        write_flac(path, sample_rate, audio.astype(np.float32))

    return subsets


def write_recording(
    run_directory: Path,
    item: str,
    audio: np.ndarray,
    sample_rate: int,
) -> None:
    """Write the recording a run reconstructs an item from, as the reconstructor prepared it."""
    directory = run_directory / RECORDINGS_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    write_flac(directory / get_filename(item, EXT_FILE_FLAC), sample_rate, audio.astype(np.float32))


def variant_directory(run_directory: Path, variant: str) -> Path:
    """The directory a variant's renders lie in."""
    return run_directory / RENDERS_DIRECTORY / variant


def item_directory(run_directory: Path, variant: str, item: str) -> Path:
    """The directory an item's per-channel clips lie in, beside the render they are parts of."""
    return variant_directory(run_directory, variant) / item
