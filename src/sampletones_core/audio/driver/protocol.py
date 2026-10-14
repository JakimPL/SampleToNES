from typing import Callable, Optional, Protocol

from .device import DriverDevice


class OutputStreamProtocol(Protocol):
    """A blocking output stream: the device plays mono float32 blocks in the order they are written.

    A write returns once the device has room for the block, so the writer is paced by the device's own
    clock. A stream ends one of two ways. A drain plays out what the device still holds, which is how a
    sound that reached its end lets its tail be heard. A close releases the stream and discards whatever
    the device still holds, which is how a sound stopped or taken over goes quiet at once.
    """

    def write(self, data: bytes) -> None:
        """Hands one block to the device, returning once the device has room for it.

        Raises:
            OSError: If the device fails the write.
        """

    def drain(self) -> None:
        """Plays out what the device still holds, and stops the stream.

        Raises:
            OSError: If the device fails to stop the stream.
        """

    def close(self) -> None:
        """Releases the stream, discarding whatever the device still holds.

        Raises:
            OSError: If the device fails to close the stream.
        """


class AudioDriverProtocol(Protocol):
    """The audio backend as the device manager reaches it: the devices it lists and the streams it opens.

    One driver is one instance of the backend. Its device indices hold until it is terminated, so a
    refresh terminates the driver and creates the next one through the factory the manager was given.
    """

    def device_count(self) -> int:
        """How many devices the backend lists, inputs included."""

    def device(self, index: int) -> DriverDevice:
        """The device the backend lists at ``index``."""

    def default_output_index(self) -> Optional[int]:
        """The index of the device the system plays through by default, or ``None`` where it names none."""

    def supports(self, index: int, sample_rate: int) -> bool:
        """Whether the device at ``index`` plays mono float32 at ``sample_rate``."""

    def open_output(
        self,
        *,
        device_index: int,
        sample_rate: int,
        frames_per_buffer: Optional[int],
    ) -> OutputStreamProtocol:
        """Opens a blocking output stream on a device.

        Args:
            device_index: The device the stream plays through.
            sample_rate: The rate the stream plays at.
            frames_per_buffer: The frames the device takes per buffer, or ``None`` for the backend's choice.

        Raises:
            OSError: If the device refuses the stream.
        """

    def terminate(self) -> None:
        """Releases the backend, which closes every stream still open on it."""


AudioDriverFactory = Callable[[], AudioDriverProtocol]
