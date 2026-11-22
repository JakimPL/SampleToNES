from typing import Mapping, Optional, Sequence

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_tools.calibration.corpus.truth import Truth, sounding_pitches
from sampletones_tools.calibration.referee.protocol import Judgment
from sampletones_tools.corpus.written import NO_RECORDINGS, WRITTEN_COEFFICIENT, WRITTEN_SCALE, written_reconstruction


def written_truth(instructions: Mapping[ChannelName, Sequence[InstructionUnion]]) -> Truth:
    """The truth of a sound written as ``instructions``, its pitch lines read from them."""
    return Truth(
        instructions={channel: tuple(stream) for channel, stream in instructions.items()},
        pitches={channel.value: line for channel, line in sounding_pitches(instructions, Config()).items()},
    )


def converted(instructions: Mapping[ChannelName, Sequence[InstructionUnion]]) -> Reconstruction:
    """A conversion that chose ``instructions``."""
    return scaled_conversion(instructions, WRITTEN_COEFFICIENT)


def scaled_conversion(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]], coefficient: float
) -> Reconstruction:
    """A conversion that chose ``instructions`` after scaling its sound down by ``coefficient``."""
    return written_reconstruction(
        {channel: list(stream) for channel, stream in instructions.items()},
        coefficient=coefficient,
        scale=WRITTEN_SCALE,
        audio_filepath=NO_RECORDINGS,
    )


def judged(judgment: Optional[Judgment]) -> Judgment:
    """The judgment a referee gave, which a test of a sound it reads expects."""
    assert judgment is not None
    return judgment
