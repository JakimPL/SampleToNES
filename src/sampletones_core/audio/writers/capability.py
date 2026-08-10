from dataclasses import dataclass
from typing import Final, Mapping, Tuple

from sampletones_core.constants.audio import SAMPLE_RATES
from sampletones_core.paths import EXT_FILE_MP3, EXT_FILE_WAVE

from .bitrate import MP3_SAMPLE_RATES
from .format import AUDIO_DEPTHS, AudioDepth, AudioFormat


@dataclass(frozen=True)
class FormatCapability:
    """What one container holds, as the format itself defines it.

    A chooser reads this to offer the settings a format accepts, and a specification is checked
    against it before a file is opened, so a combination the encoder would reject is caught while
    it is still a request.

    Attributes:
        extension: The suffix a file of this format carries.
        sample_rates: The rates the format encodes, lowest first.
        depths: The sample forms the format stores, coarsest first; empty where the format sets
            its own and offers a bitrate instead.
    """

    extension: str
    sample_rates: Tuple[int, ...]
    depths: Tuple[AudioDepth, ...]

    @property
    def stores_samples(self) -> bool:
        """Whether the format stores samples directly, which is what gives it a depth to choose."""
        return bool(self.depths)

    def supports_sample_rate(self, sample_rate: int) -> bool:
        return sample_rate in self.sample_rates

    def supports_depth(self, depth: AudioDepth) -> bool:
        return depth in self.depths


FORMAT_CAPABILITIES: Final[Mapping[AudioFormat, FormatCapability]] = {
    AudioFormat.WAVE: FormatCapability(
        extension=EXT_FILE_WAVE,
        sample_rates=tuple(SAMPLE_RATES),
        depths=AUDIO_DEPTHS,
    ),
    AudioFormat.MP3: FormatCapability(
        extension=EXT_FILE_MP3,
        sample_rates=MP3_SAMPLE_RATES,
        depths=(),
    ),
}


def capability_of(audio_format: AudioFormat) -> FormatCapability:
    """What ``audio_format`` holds.

    Args:
        audio_format: The container to describe.

    Returns:
        FormatCapability: The settings that format accepts.

    Raises:
        KeyError: If the format has no entry in the registry.
    """
    return FORMAT_CAPABILITIES[audio_format]
