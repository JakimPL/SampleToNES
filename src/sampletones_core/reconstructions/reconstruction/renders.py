from typing import Dict, List

import numpy as np

from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators.render import render_channels
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction


def sounding_streams(reconstruction: Reconstruction) -> List[InstructionsItem]:
    """The streams that describe a frame, in channel order, which are the channels a render sounds."""
    return [stream for stream in reconstruction.instructions_data if stream.instructions]


def rendered_channels(reconstruction: Reconstruction) -> Dict[ChannelName, np.ndarray]:
    """The audio each channel in play renders from the instructions it carries.

    A reconstruction records the instructions a channel plays, so its sound is read from those
    each time it is asked for. A reader that asks again and again keeps the answer where it
    governs how long the audio lives, such as the application's render cache.
    """
    return render_channels(reconstruction.instructions, reconstruction.config)


def rendered_mix(reconstruction: Reconstruction) -> np.ndarray:
    """The whole reconstruction, summed from the channels that play."""
    return mix(list(rendered_channels(reconstruction).values()))


def rendered_length(reconstruction: Reconstruction) -> int:
    """How many samples the rendered reconstruction spans: its longest stream, frame by frame."""
    frames = max((len(stream) for stream in reconstruction.instructions.values()), default=0)
    return frames * reconstruction.config.frame_length
