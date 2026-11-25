import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Dict, Final, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, ordered_channels
from sampletones_core.generators import GeneratorUnion, TonalGenerator, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, TonalInstruction

LINE: Final[str] = "line"
FRAME_MIDDLE: Final[float] = 0.5
FIRST_FRAME: Final[int] = 0

PitchLine = Tuple[Optional[float], ...]
TimeFunction = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class Truth:
    """What a reference sound plays, frame by frame at the run's frame rate, as it was made.

    A sound carries the truth its making allows. A sound written as NES frames is exactly what its
    frames render to, so it carries the frames themselves, and a conversion is held to them frame for
    frame. A synthesized sound is one the channels approximate, so it carries the pitch its voice
    sounds. A recording's truth is ``None``.

    Attributes:
        instructions: The instructions each channel plays, for a sound written out as NES frames;
            empty for a synthesized one.
        pitches: The frequency in Hz each line of the sound sounds in every frame, ``None`` where the
            line is silent, keyed by the line's name. A written sound names one line per tonal channel
            it writes, by the channel's name, and a synthesized one names its lines by the parts it
            plays, ``LINE`` where it plays one.
    """

    instructions: Mapping[ChannelName, Tuple[InstructionUnion, ...]]
    pitches: Mapping[str, PitchLine]


def frame_middles(first: int, count: int, frame_rate: int) -> np.ndarray:
    """The time in seconds at the middle of each of ``count`` frames from ``first`` on.

    A frame's truth is read at its middle, so a change falling on the edge between two frames
    belongs to the frame it starts and leaves the frame before it whole.
    """
    return (np.arange(first, first + count) + FRAME_MIDDLE) / frame_rate


def frames_reached(samples: int, sample_rate: int, frame_rate: int) -> int:
    """How many frames ``samples`` of audio at ``sample_rate`` reach into, the last of them partly.

    A synthesized sound's line covers every frame its rendered audio reaches. The count is taken in
    whole numbers, so audio ending on a frame's edge reaches the frames before it alone.
    """
    return math.ceil(Fraction(samples * frame_rate, sample_rate))


def pitch_line(frequency_at: TimeFunction, sounding_at: TimeFunction, frames: int, frame_rate: int) -> PitchLine:
    """The frequency a synthesized sound sounds at the middle of each of its first ``frames`` frames.

    A frame where the sound counts as silent holds ``None``.

    Args:
        frequency_at: The frequency in Hz the sound sounds at each time.
        sounding_at: Whether the sound counts as sounding its pitch at each time.
        frames: How many frames the line covers.
        frame_rate: The frames per second.

    Returns:
        PitchLine: One frequency per frame, ``None`` where the sound counts as silent.
    """
    times = frame_middles(FIRST_FRAME, frames, frame_rate)
    return tuple(
        float(frequency) if heard else None for frequency, heard in zip(frequency_at(times), sounding_at(times))
    )


def steady(frequency: float, times: np.ndarray) -> np.ndarray:
    """The one frequency a sound holding one pitch sounds, at every time."""
    return np.full_like(times, frequency)


def audible(level_at: TimeFunction, audible_floor: float, times: np.ndarray) -> np.ndarray:
    """Whether a sound stands at or above ``audible_floor`` of its full level at each time.

    ``level_at`` gives the sound's level against its full level, so a decay counts as sounding its
    pitch until it falls below the floor, and a crescendo from where it rises to it. A fair test of a
    pitch ends where the sound grows too quiet to carry it.
    """
    return np.asarray(level_at(times) >= audible_floor)


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
    generators = get_generators_by_channels(config, ordered_channels(TONE_CHANNELS))
    return {
        channel: tuple(_sounding(generators[channel], instruction) for instruction in stream)
        for channel, stream in instructions.items()
        if channel in TONE_CHANNELS
    }


def _sounding(generator: GeneratorUnion, instruction: InstructionUnion) -> Optional[float]:
    """The frequency ``generator`` sounds ``instruction`` at, ``None`` where the frame is off."""
    match instruction:
        case TonalInstruction(on=True) if isinstance(generator, TonalGenerator):
            return generator.sounds_at(instruction.pitch, instruction.timer_offset)
        case _:
            return None
