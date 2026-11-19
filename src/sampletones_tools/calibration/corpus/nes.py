from typing import Dict, Final, FrozenSet, List, Mapping, Sequence, Tuple

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.generators import render_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_tools.calibration.config.sequences import SequencesConfig
from sampletones_tools.corpus.written import channel_frames

from .families import Family
from .item import CorpusItem
from .truth import Truth, sounding_pitches

ROUND_TRIP_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


def written_item(
    name: str,
    family: Family,
    category: str,
    *,
    listed: bool,
    instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    config: Config,
) -> CorpusItem:
    """A reference sound written out as NES frames, rendered the way the channels play it.

    The sound carries the frames it was written as, so its conversion is measured against what it
    plays, and it is converted over every channel, so a round trip also answers which channels stay
    silent.

    Args:
        name: The name its files are written under.
        family: The family it belongs to.
        category: The kind of decision it tests.
        listed: Whether the page lists it.
        instructions: What each channel plays, one instruction per frame.
        config: The configuration the frames are rendered at, the one the run converts with.

    Returns:
        CorpusItem: The sound with its truth.
    """
    frames: Dict[ChannelName, Tuple[InstructionUnion, ...]] = {
        channel: tuple(stream) for channel, stream in instructions.items()
    }
    audio = mix(list(render_channels(frames, config).values()))
    pitches = {channel.value: line for channel, line in sounding_pitches(frames, config).items()}
    return CorpusItem(
        name=name,
        family=family,
        category=category,
        listed=listed,
        audio=np.asarray(audio, dtype=np.float32),
        truth=Truth(instructions=frames, pitches=pitches),
        channels=ROUND_TRIP_CHANNELS,
    )


def held(channel: ChannelName, instruction: InstructionUnion, *, sounding: int, silent: int) -> List[InstructionUnion]:
    """An instruction held for ``sounding`` frames, then ``silent`` frames of the channel's silence."""
    silence = CHANNEL_TO_EXPORTER_MAP[channel].get_instruction_type().null_instruction()
    return [instruction] * sounding + [silence] * silent


def build_sequences(config: Config, *, corpus: SequencesConfig) -> List[CorpusItem]:
    """The sequences written out as NES frames, each a listed sound of the ``sequences`` family.

    Args:
        config: The configuration the frames are rendered at, the one the run converts with.
        corpus: The written sequences.

    Returns:
        List[CorpusItem]: One item per sequence, in the order the corpus lists them.
    """
    return [
        written_item(
            sequence.name,
            Family.SEQUENCES,
            sequence.category,
            listed=True,
            instructions={channel: channel_frames(channel, runs) for channel, runs in sequence.channels.items()},
            config=config,
        )
        for sequence in corpus.items
    ]
