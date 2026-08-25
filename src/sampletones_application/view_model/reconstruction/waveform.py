from dataclasses import dataclass

import numpy as np

from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class InstrumentWaveformViewModel:
    """What a hand-written voice sounds like, as the plot card draws it.

    An instrument stands on no recording, so the card shows the audio its envelopes make on the
    generator chosen to hear it: one line under the voice's own name, in that generator's color.

    Attributes:
        name: The name the series is labeled by, which is the voice's own.
        channel_name: The channel the audio was rendered on, naming the color it is drawn in.
        audio: The waveform, one frame per tick the envelopes describe.
        frame_length: The samples one frame spans, which the per-frame overlay reads.
    """

    name: str
    channel_name: ChannelName
    audio: np.ndarray
    frame_length: int
