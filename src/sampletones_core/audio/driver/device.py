from dataclasses import dataclass


@dataclass(frozen=True)
class DriverDevice:
    """One device as the audio backend lists it, before the manager asks which rates it plays.

    Attributes:
        index: The backend's index for the device, valid until the backend is created again.
        name: The device's name, in UTF-8.
        max_output_channels: How many channels the device plays at once; zero for an input alone.
        default_sample_rate: The rate the device plays at unless asked for another.
        host_api: The backend's index of the host API the device belongs to.
    """

    index: int
    name: str
    max_output_channels: int
    default_sample_rate: int
    host_api: int

    @property
    def plays_output(self) -> bool:
        """Whether the device can play audio, which is what the output list offers."""
        return self.max_output_channels > 0
