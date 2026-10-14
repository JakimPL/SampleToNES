from typing import Final

from .device import FakeDevice

SPEAKERS: Final[FakeDevice] = FakeDevice(
    name="Speakers",
    default_sample_rate=44100,
    supported_sample_rates=(44100, 48000),
    output_channels=2,
    host_api=0,
)
HEADPHONES: Final[FakeDevice] = FakeDevice(
    name="Headphones",
    default_sample_rate=48000,
    supported_sample_rates=(48000, 96000),
    output_channels=2,
    host_api=0,
)
MICROPHONE: Final[FakeDevice] = FakeDevice(
    name="Microphone",
    default_sample_rate=44100,
    supported_sample_rates=(44100,),
    output_channels=0,
    host_api=0,
)
