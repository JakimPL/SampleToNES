import threading
from dataclasses import dataclass
from typing import Callable, Final, Generic, List, Tuple, TypeVar

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.bridge import ONE_FRAME, RenderThread

ReadingT = TypeVar("ReadingT")
NO_FRAME: Final[int] = 0


@dataclass(frozen=True)
class FrameReading(Generic[ReadingT]):
    """What one reading found right after one frame was drawn."""

    frame: int
    value: ReadingT


class FrameRecording(Generic[ReadingT]):
    """A reading taken right after every frame between a start and a stop, on the render thread.

    An expectation reads once a frame until it holds, and so misses a state lasting a single frame.
    A recording keeps every frame's reading, so a scenario asserting that something never happened
    between two gestures reads each frame that passed.
    """

    def __init__(
        self,
        render_thread: RenderThread,
        reading: Callable[[], ReadingT],
    ) -> None:
        self._render_thread = render_thread
        self._reading = reading
        self._readings: List[FrameReading[ReadingT]] = []
        self._stopped = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        """Takes the first reading after the next frame and goes on reading after every frame."""
        self._render_thread.post(self._take, frames=ONE_FRAME)

    def stop(self) -> None:
        """Ends the recording; the readings taken so far stay available."""
        self._stopped.set()

    @property
    def readings(self) -> Tuple[FrameReading[ReadingT], ...]:
        """Every reading taken so far, in frame order, each with the frame it followed."""
        with self._lock:
            return tuple(self._readings)

    def values(self) -> List[ReadingT]:
        """The value of every reading taken so far, in frame order."""
        return [reading.value for reading in self.readings]

    def _take(self) -> None:
        if self._stopped.is_set():
            return

        reading = FrameReading(frame=dpg.get_frame_count(), value=self._reading())
        with self._lock:
            self._readings.append(reading)

        self._render_thread.post(self._take, frames=ONE_FRAME)
