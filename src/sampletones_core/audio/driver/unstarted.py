from typing import Final, Optional

from .device import DriverDevice
from .protocol import OutputStreamProtocol

NO_DEVICES: Final[int] = 0


class UnstartedDriver:
    """The backend that stands in where the audio system refused to start: it lists no device.

    The application then opens as it does on a machine offering no output, tells the reader so when a
    sound is asked for, and a refresh asks the audio system to start again.
    """

    def device_count(self) -> int:
        return NO_DEVICES

    def device(self, index: int) -> DriverDevice:
        """Lists nothing, since an audio system that refused to start offers no device.

        Raises:
            IndexError: Always, since no index names a device.
        """
        raise IndexError(f"the audio system refused to start, so it lists no device at {index}")

    def default_output_index(self) -> Optional[int]:
        return None

    def supports(self, index: int, sample_rate: int) -> bool:
        return False

    def open_output(
        self,
        *,
        device_index: int,
        sample_rate: int,
        frames_per_buffer: Optional[int],
    ) -> OutputStreamProtocol:
        """Opens nothing, since an audio system that refused to start offers no device.

        Raises:
            OSError: Always, since no device takes a stream.
        """
        raise OSError(f"the audio system refused to start, so device {device_index} takes no stream")

    def terminate(self) -> None:
        return None
