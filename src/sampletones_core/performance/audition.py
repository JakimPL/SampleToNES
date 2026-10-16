from typing import List, Optional

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features.envelope import release_length
from sampletones_core.generators.render import render_instructions
from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.live import LiveNote
from sampletones_core.project.patterns.pitch import Note
from sampletones_core.project.voices.instrument import Instrument


def audition_ticks(instrument: Instrument, *, cap: int) -> int:
    """How long an audition of one voice sounds, in ticks.

    A voice whose volume ends at silence releases itself, so it is sounded through to that release
    and stops where a tracker row holding it would. One that circles from a loop point goes on for
    as long as it is asked to, so it sounds for ``cap`` — the length an audition offers a voice
    that never ends of its own accord.

    Args:
        instrument: The voice being sounded.
        cap: The ticks a voice sounds for where it states no release of its own.

    Returns:
        int: The ticks the audition sounds.
    """
    length = release_length(instrument.envelopes.volume)
    return cap if length is None else length


def audition_instructions(
    instrument: Instrument,
    channel_name: ChannelName,
    *,
    pitch: int,
    ticks: int,
) -> List[InstructionUnion]:
    """The frames an instrument sounds on one channel at one note, at full volume.

    An audition is a live note held for ``ticks`` ticks, so it sounds what a tracker row holding the note
    sounds: the step from the voice's reference to the note, each dimension the voice leaves empty at the
    value a note starts on, and the frames past the written ones circling from their loop points or
    holding their last items.

    Args:
        instrument: The voice being sounded.
        channel_name: The channel it is sounded on.
        pitch: The note it sounds at, read as a period on the noise channel.
        ticks: How many ticks to sound, as :func:`audition_ticks` counts them.

    Returns:
        List[InstructionUnion]: The frames, empty where the instrument writes no envelope.
    """
    note = LiveNote.of_voice(
        instrument,
        pitches={channel_name: Note(value=pitch)},
        levels={channel_name: MAX_VOLUME},
    )
    if channel_name not in note.channel_names:
        return []

    frames: List[InstructionUnion] = []
    for _ in range(ticks):
        instruction = note.tick()[channel_name]
        if instruction is not None:
            frames.append(instruction)

    return frames


def audition_audio(
    instrument: Instrument,
    channel_name: ChannelName,
    config: Config,
    *,
    pitch: int,
    ticks: int,
) -> Optional[np.ndarray]:
    """The audio an instrument sounds on one channel at one note.

    This is what an audition plays and what a plot of an instrument draws, so both answer
    the same generator with the same waveform over the same span.

    Args:
        instrument: The voice being sounded.
        channel_name: The channel it is sounded on.
        config: The configuration the frames are rendered at.
        pitch: The note it sounds at, read as a period on the noise channel.
        ticks: How many ticks to sound, as :func:`audition_ticks` counts them.

    Returns:
        Optional[np.ndarray]: The waveform to play, or ``None`` where the instrument
        writes no envelope for that channel.
    """
    instructions = audition_instructions(
        instrument,
        channel_name,
        pitch=pitch,
        ticks=ticks,
    )
    if not instructions:
        return None

    return render_instructions(instructions, channel_name, config)
