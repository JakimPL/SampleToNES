from typing import Dict, Final, FrozenSet, List, Tuple

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import render_channels
from sampletones_core.instructions import InstructionUnion
from sampletones_tools.calibration.config.nes import NesCorpusConfig, NesItemConfig
from sampletones_tools.corpus.written import channel_frames

from .item import CorpusItem
from .truth import Truth, sounding_pitches

ROUND_TRIP_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


def build_nes_corpus(config: Config, *, corpus: NesCorpusConfig) -> List[CorpusItem]:
    """The reference sounds written out as NES frames, each rendered the way the channels play it.

    Each sound carries the frames it was written as, so its conversion is measured against what it
    plays, and it is converted over every channel, so a round trip also answers which channels stay
    silent.

    Args:
        config: The configuration the frames are rendered at, the one the run converts with.
        corpus: The written reference sounds.

    Returns:
        List[CorpusItem]: One item per written sound, in the order the corpus lists them.
    """
    return [_written_item(item, config) for item in corpus.items]


def _written_item(item: NesItemConfig, config: Config) -> CorpusItem:
    instructions: Dict[ChannelName, Tuple[InstructionUnion, ...]] = {
        channel: tuple(channel_frames(channel, runs)) for channel, runs in item.channels.items()
    }
    audio = mix(list(render_channels(instructions, config).values()))
    pitches = {channel.value: line for channel, line in sounding_pitches(instructions, config).items()}
    return CorpusItem(
        name=item.name,
        category=item.category,
        audio=np.asarray(audio, dtype=np.float32),
        truth=Truth(instructions=instructions, pitches=pitches),
        channels=ROUND_TRIP_CHANNELS,
    )
