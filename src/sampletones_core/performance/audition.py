from typing import List, Optional

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.modifiers import apply_modifiers
from sampletones_core.project.voices.instrument import Instrument


def audition_instructions(
    instrument: Instrument,
    channel_name: ChannelName,
    *,
    pitch: int,
) -> List[InstructionUnion]:
    """The frames an instrument sounds on one channel at one note, at full volume.

    An instrument's frames are built at the reference the channel reads, so sounding it at a note
    is the step from that reference to the note — the same step a tracker row states, taken here
    without a row to state it. The whole envelope is sounded through, which is what a listener
    hears of a voice standing on its own.

    Args:
        instrument: The voice being sounded.
        channel_name: The channel it is sounded on.
        pitch: The note it sounds at, read as a period on the noise channel.

    Returns:
        List[InstructionUnion]: The frames, empty where the instrument writes no envelope.
    """
    transpose = pitch - instrument.reference(channel_name)
    return [
        apply_modifiers(instruction, transpose, MAX_VOLUME) for instruction in instrument.instructions(channel_name)
    ]


def audition_audio(
    instrument: Instrument,
    channel_name: ChannelName,
    config: Config,
    *,
    pitch: int,
) -> Optional[np.ndarray]:
    """The audio an instrument sounds on one channel at one note.

    This is what an audition plays and what a plot of a hand-written voice draws, so both answer
    the same generator with the same waveform.

    Args:
        instrument: The voice being sounded.
        channel_name: The channel it is sounded on.
        config: The configuration the frames are rendered at.
        pitch: The note it sounds at, read as a period on the noise channel.

    Returns:
        Optional[np.ndarray]: The waveform to play, or ``None`` where the instrument
        writes no envelope for that channel.
    """
    instructions = audition_instructions(instrument, channel_name, pitch=pitch)
    if not instructions:
        return None

    return render_instructions(instructions, channel_name, config)
