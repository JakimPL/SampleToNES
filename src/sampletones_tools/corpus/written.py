from pathlib import Path
from typing import Final, Mapping, Sequence, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

SINGLE_STEM_ID: Final[int] = 0


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
