from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class OpenCall:
    """One open reaching the fake device: the device, the rate and the buffer it asks for."""

    device: int
    sample_rate: int
    frames_per_buffer: Optional[int]


@dataclass(frozen=True)
class StreamCall:
    """One call reaching an open stream: which stream, how many writes it took before, and the frames carried."""

    stream: int
    writes: int
    frames: int


OpenHook = Callable[[OpenCall], None]
StreamHook = Callable[[StreamCall], None]
