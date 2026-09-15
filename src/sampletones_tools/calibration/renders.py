from pathlib import Path
from typing import Dict, Final, Mapping, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.audio.io import write_wave
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.paths.extensions import EXT_FILE_JSON, EXT_FILE_WAVE
from sampletones_shared.utils.system.paths import get_filename

from .layout import RECORDINGS_DIRECTORY, RENDERS_DIRECTORY

SOUNDING_FRAME: Final[str] = "1"
RESTING_FRAME: Final[str] = "0"


class RenderRecord(BaseModel):
    """
    What a calibration run heard in one render: the scores it drew and which channel sounded when.

    A record sits beside its render's WAV file, so a run can be studied after it ends from what it
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
    directory = run_directory / RENDERS_DIRECTORY / record.variant
    directory.mkdir(parents=True, exist_ok=True)
    write_wave(directory / get_filename(record.item, EXT_FILE_WAVE), sample_rate, audio.astype(np.float32))
    (directory / get_filename(record.item, EXT_FILE_JSON)).write_text(
        record.model_dump_json(indent=1), encoding="utf-8"
    )


def write_recording(
    run_directory: Path,
    item: str,
    audio: np.ndarray,
    sample_rate: int,
) -> None:
    """Write the recording a run reconstructs an item from, as the reconstructor prepared it."""
    directory = run_directory / RECORDINGS_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    write_wave(directory / get_filename(item, EXT_FILE_WAVE), sample_rate, audio.astype(np.float32))
