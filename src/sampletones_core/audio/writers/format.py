from enum import StrEnum
from typing import Final, Mapping, Tuple


class AudioFormat(StrEnum):
    """The container a rendered song is written into."""

    WAVE = "wave"
    MP3 = "mp3"


class AudioDepth(StrEnum):
    """The form each sample takes in a file that stores samples directly.

    The integer depths quantize the signal to a fixed number of steps, coarsest first; the float
    depth stores the rendered value as it stands. Eight bits gives 256 steps across the range, the
    grain a chip render is often chosen for.
    """

    PCM_U8 = "pcm_u8"
    PCM_16 = "pcm_16"
    PCM_24 = "pcm_24"
    PCM_32 = "pcm_32"
    FLOAT_32 = "float_32"

    @property
    def bits(self) -> int:
        """The bits one stored sample occupies."""
        return DEPTH_BITS[self]


DEPTH_BITS: Final[Mapping[AudioDepth, int]] = {
    AudioDepth.PCM_U8: 8,
    AudioDepth.PCM_16: 16,
    AudioDepth.PCM_24: 24,
    AudioDepth.PCM_32: 32,
    AudioDepth.FLOAT_32: 32,
}

AUDIO_DEPTHS: Final[Tuple[AudioDepth, ...]] = (
    AudioDepth.PCM_U8,
    AudioDepth.PCM_16,
    AudioDepth.PCM_24,
    AudioDepth.PCM_32,
    AudioDepth.FLOAT_32,
)

DEFAULT_AUDIO_FORMAT: Final[AudioFormat] = AudioFormat.WAVE
DEFAULT_AUDIO_DEPTH: Final[AudioDepth] = AudioDepth.PCM_16
