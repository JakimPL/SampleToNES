from enum import IntEnum


class PlaybackPriority(IntEnum):
    """Relative importance of an audio-output request.

    The audio device exposes a single output, so competing requests are ranked: a lower-priority
    request yields to active higher-priority playback. Browser autoplay is an auxiliary preview;
    the reconstruction/instrument players and the sequencer song player are intentional.
    """

    PREVIEW = 0
    NORMAL = 1
