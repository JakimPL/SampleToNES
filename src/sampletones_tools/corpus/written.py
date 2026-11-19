from pathlib import Path
from typing import Dict, Final, List, Mapping, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

SINGLE_STEM_ID: Final[int] = 0
WRITTEN_COEFFICIENT: Final[float] = 1.0
WRITTEN_SCALE: Final[float] = 1.0
NO_RECORDINGS: Final[Tuple[Path, ...]] = ()

FrameValue = Union[bool, int]


class FrameRun(BaseModel):
    """Frames one channel plays alike, one after another.

    Attributes:
        count: How many frames the run lasts.
        frame: The instruction each of those frames plays, in the fields the channel's instruction takes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    count: int = Field(..., ge=1)
    frame: Dict[str, FrameValue]


def channel_frames(
    channel: ChannelName,
    runs: Sequence[FrameRun],
) -> List[InstructionUnion]:
    """The frames one channel plays, each run read as the instruction that channel takes.

    Args:
        channel: The channel the frames play on.
        runs: The runs of alike frames, in order.

    Returns:
        List[InstructionUnion]: One instruction per frame.

    Raises:
        ValidationError: If a run's frame is no instruction the channel takes.
    """
    instruction_type = CHANNEL_TO_EXPORTER_MAP[channel].get_instruction_type()
    frames: List[InstructionUnion] = []
    for run in runs:
        frame = instruction_type.model_validate(run.frame)
        frames.extend(frame for _ in range(run.count))

    return frames


def single_recording_record(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    scale: float,
) -> StemsData:
    """The single-entry record a classic conversion writes over the frames it chose.

    A frame that sounds answers to the one recording, and a silent frame answers to rest, which is
    the rule a reconstruction holds its record to.

    Args:
        instructions: What each channel plays, one instruction per frame.
        scale: The level the recording was read at.

    Returns:
        StemsData: The record naming one owner per frame.
    """
    assignments = [
        ChannelAssignment(
            channel_name=channel_name,
            stem_ids=tuple(SINGLE_STEM_ID if instruction.on else RESTING_STEM_ID for instruction in stream),
        )
        for channel_name, stream in instructions.items()
    ]
    return StemsData.single_entry(
        StemSettings.covering(list(instructions)),
        assignments,
        scale,
    )


def written_reconstruction(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    *,
    coefficient: float,
    scale: float,
    audio_filepath: Tuple[Path, ...],
) -> Reconstruction:
    """A reconstruction playing the frames it is given, as though one conversion had chosen them.

    Writing the frames out by hand is what lets a corpus state exactly what each channel sounds on
    every tick.

    Args:
        instructions: What each channel plays, one instruction per frame.
        coefficient: The working-level coefficient the recording is said to be scaled by.
        scale: The level the recording is said to be read at.
        audio_filepath: The recordings the frames are said to come from, empty for none.

    Returns:
        Reconstruction: The document holding those frames and the record behind them.
    """
    return Reconstruction.create(
        instructions=instructions,
        config=Config(),
        coefficient=coefficient,
        audio_filepath=audio_filepath,
        stems_data=single_recording_record(
            instructions,
            scale,
        ),
    )


def written_runs(runs_by_channel: Mapping[ChannelName, Sequence[FrameRun]]) -> Reconstruction:
    """A reconstruction playing the runs each channel writes out, at unit level with no recording behind it.

    Raises:
        ValidationError: If a run's frame is no instruction its channel takes.
    """
    return written_reconstruction(
        {channel: channel_frames(channel, runs) for channel, runs in runs_by_channel.items()},
        coefficient=WRITTEN_COEFFICIENT,
        scale=WRITTEN_SCALE,
        audio_filepath=NO_RECORDINGS,
    )
