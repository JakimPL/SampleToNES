from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_core.generators import GeneratorUnion, TonalGenerator, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, TonalInstruction

PitchLine = Tuple[Optional[float], ...]


@dataclass(frozen=True)
class Truth:
    """What a reference sound plays, frame by frame, as it was made.

    Attributes:
        instructions: The instructions each channel plays, for a sound written out as NES frames;
            empty for a synthesized one.
        pitches: The frequency in Hz each line of the sound sounds in every frame, ``None`` where the
            line is silent, keyed by the line's name.
    """

    instructions: Mapping[ChannelName, Tuple[InstructionUnion, ...]]
    pitches: Mapping[str, PitchLine]


def sounding_pitches(
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    config: Config,
) -> Dict[ChannelName, PitchLine]:
    """The frequency each tonal channel sounds in every frame, ``None`` where it is off.

    A frame sounds where its channel's generator puts the note once the frame's bend has moved it,
    so the triangle sounds an octave below a pulse playing the same note.

    Args:
        instructions: The instructions each channel plays, one per frame.
        config: The configuration the frames are rendered at.

    Returns:
        Dict[ChannelName, PitchLine]: One line per tonal channel among ``instructions``.
    """
    generators = get_generators_by_channels(config, [name for name in ChannelName.items() if name in TONE_CHANNELS])
    return {
        channel: tuple(_sounding(generators[channel], instruction) for instruction in stream)
        for channel, stream in instructions.items()
        if channel in TONE_CHANNELS
    }


def _sounding(generator: GeneratorUnion, instruction: InstructionUnion) -> Optional[float]:
    match instruction:
        case TonalInstruction(on=True) if isinstance(generator, TonalGenerator):
            return generator.sounds_at(instruction.pitch, instruction.timer_offset)
        case _:
            return None
