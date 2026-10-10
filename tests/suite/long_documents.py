from pathlib import Path
from typing import Dict, Final, List, Sequence, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.reconstructions import Reconstruction
from tests.suite.stems import recorded_from, single_entry_stems_data

LOWEST_PITCH: Final[int] = 36
PITCH_SPAN: Final[int] = 48
VOLUMES: Final[int] = 16
DUTY_CYCLES: Final[int] = 4
NOISE_PERIODS: Final[int] = 16
UNIT_COEFFICIENT: Final[float] = 1.0
NO_RECORDINGS: Final[Tuple[Path, ...]] = ()


def turning_instruction(
    channel_name: ChannelName,
    frame: int,
) -> InstructionUnion:
    """The instruction ``channel_name`` plays at ``frame`` of a long conversion.

    The pitch, the level and the timbre each turn with the frame, so every frame is an instruction
    of its own and a stream of them compresses as a conversion's does.
    """
    match channel_name:
        case ChannelName.PULSE1 | ChannelName.PULSE2:
            return PulseInstruction(
                on=True,
                pitch=LOWEST_PITCH + frame % PITCH_SPAN,
                volume=frame % VOLUMES,
                duty_cycle=frame % DUTY_CYCLES,
            )
        case ChannelName.TRIANGLE:
            return TriangleInstruction(on=True, pitch=LOWEST_PITCH + frame % PITCH_SPAN)
        case ChannelName.NOISE:
            return NoiseInstruction(on=True, period=frame % NOISE_PERIODS, volume=frame % VOLUMES, short=False)


def turning_instructions(frames: int) -> Dict[ChannelName, List[InstructionUnion]]:
    """Every channel sounding through ``frames`` frames, each frame an instruction of its own."""
    return {
        channel_name: [turning_instruction(channel_name, frame) for frame in range(frames)]
        for channel_name in ChannelName.items()
    }


def long_document(
    seconds: float,
    *,
    config: Config,
    recordings: Sequence[Path] = NO_RECORDINGS,
) -> Reconstruction:
    """A document shaped like a long conversion, lasting ``seconds`` at the rate ``config`` runs at.

    Every channel sounds through every frame. With ``recordings``, the frames are shared out among
    them in turn: the document names one recording per path, and each channel plays its part once
    per recording, so a reader can leave a recording out and hear the rest.
    """
    frames = round(seconds * config.nes_frequency)
    if not recordings:
        instructions = turning_instructions(frames)
        return Reconstruction.create(
            instructions=instructions,
            config=config,
            coefficient=UNIT_COEFFICIENT,
            audio_filepath=(),
            stems_data=single_entry_stems_data(ChannelName.items(), instructions),
        )

    instructions = turning_instructions(frames // len(recordings))
    document = Reconstruction.create(
        instructions=instructions,
        config=config,
        coefficient=UNIT_COEFFICIENT,
        audio_filepath=tuple(recordings[:1]),
        stems_data=single_entry_stems_data(ChannelName.items(), instructions),
    )
    return recorded_from(document, recordings)
