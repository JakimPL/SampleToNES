from dataclasses import dataclass
from typing import Optional

from sampletones_core.audio.device import CurrentDevice
from sampletones_core.constants.audio import BufferSize


@dataclass(frozen=True)
class OutputSettings:
    """What the next stream opens with: the device and the rate it plays at, and the frames it takes per buffer.

    Attributes:
        device: The device in force and its rate, or ``None`` while no device is chosen, which refuses every sound.
        buffer_size: The frames the device takes per buffer, which is also the block the writer hands it.
    """

    device: Optional[CurrentDevice]
    buffer_size: BufferSize
