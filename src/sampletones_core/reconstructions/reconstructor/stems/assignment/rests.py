from typing import Dict, FrozenSet, Sequence, Tuple

import numpy as np

from sampletones_core.constants.algorithm import RESTING_FRAME_COST, STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.models.rest import StemRest
from sampletones_shared.array import to_numpy


def sounding_stems(fragments: Dict[int, Fragment]) -> FrozenSet[int]:
    """The stems whose own frame reaches a level a channel can render.

    A frame quieter than the quietest note the hardware plays, measured against the working
    level, holds nothing for a channel to sound. Its stem stands aside, so the channel goes
    to a stem that does sound there or rests, and a recording silent through a passage keeps
    that passage silent on the channels it holds. A frame whose peak reaches
    ``STEM_ACTIVITY_FLOOR`` exactly sounds.
    """
    return frozenset(
        stem_id
        for stem_id, fragment in fragments.items()
        if float(np.max(np.abs(to_numpy(fragment.audio)), initial=0.0)) >= STEM_ACTIVITY_FLOOR
    )


def resting(
    channel_names: Sequence[ChannelName],
    channels: Dict[ChannelName, GeneratorUnion],
    fragment: Fragment,
) -> Tuple[StemRest, ...]:
    """The channels no stem holds in a frame, each holding its null instruction over a silent frame."""
    silence = silent_contribution(fragment)
    return tuple(
        StemRest(
            channel_name=channel_name,
            column=(
                ScoredCandidate(
                    instruction=channels[channel_name].get_instruction_type().null_instruction(),
                    cost=RESTING_FRAME_COST,
                    contribution=silence,
                ),
            ),
        )
        for channel_name in channel_names
    )


def silent_contribution(fragment: Fragment) -> Contribution:
    """What a channel playing nothing adds to ``fragment``: no power in any bin and no waveform."""
    return Contribution.silence(len(fragment.feature.values), fragment.audio.shape[0])
