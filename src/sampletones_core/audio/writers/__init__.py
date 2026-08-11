from .bitrate import (
    MP3_LADDERS,
    MP3_SAMPLE_RATES,
    default_mp3_bitrate,
    mp3_bitrates,
    mp3_compression_level,
)
from .capability import FORMAT_CAPABILITIES, FormatCapability, capability_of
from .format import (
    AUDIO_DEPTHS,
    DEFAULT_AUDIO_DEPTH,
    DEFAULT_AUDIO_FORMAT,
    AudioDepth,
    AudioFormat,
)
from .protocol import AudioWriter
from .selection import available_audio_formats, available_depths, open_audio_writer
from .soundfile import SoundFileAudioWriter
from .spec import AudioOutputSpec, AudioOutputSpecBase, Mp3OutputSpec, WaveOutputSpec

__all__ = [
    "AUDIO_DEPTHS",
    "DEFAULT_AUDIO_DEPTH",
    "DEFAULT_AUDIO_FORMAT",
    "FORMAT_CAPABILITIES",
    "MP3_LADDERS",
    "MP3_SAMPLE_RATES",
    "AudioDepth",
    "AudioFormat",
    "AudioOutputSpec",
    "AudioOutputSpecBase",
    "AudioWriter",
    "FormatCapability",
    "Mp3OutputSpec",
    "SoundFileAudioWriter",
    "WaveOutputSpec",
    "available_audio_formats",
    "available_depths",
    "capability_of",
    "default_mp3_bitrate",
    "mp3_bitrates",
    "mp3_compression_level",
    "open_audio_writer",
]
