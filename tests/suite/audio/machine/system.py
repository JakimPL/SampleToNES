import threading
from typing import List, Optional, Sequence

from tests.suite.audio.pacing import Pacing
from tests.suite.audio.timeline import Opened, Refused, Timeline, Violation, ViolationKind

from .calls import OpenCall
from .device import FakeDevice
from .driver import FakeAudioDriver
from .hooks import MachineHooks
from .messages import DEVICE_BUSY
from .stream import FakeOutputStream


class FakeAudioSystem:
    """A machine's audio as a playback meets it: its devices, the stream the device holds, and a clock.

    Every driver the manager creates is a fresh instance of this one machine's backend. The device plays
    one stream at a time, as a hardware device does, so a second open while one stands is refused as busy
    and recorded as a violation. ``occupy`` stands for another program holding the device, which is
    refused without a violation. ``hooks`` holds what a case runs at the start of each call.
    """

    def __init__(
        self,
        devices: Sequence[FakeDevice],
        *,
        default_device: Optional[int],
        pacing: Pacing,
        timeline: Timeline,
    ) -> None:
        self.devices: List[FakeDevice] = list(devices)
        self.default_device = default_device
        self.pacing = pacing
        self.timeline = timeline
        self.hooks = MachineHooks()
        self.drivers: List[FakeAudioDriver] = []
        self._lock = threading.Lock()
        self._open: List[int] = []
        self._occupied: bool = False
        self._next_stream: int = 0

    def driver(self) -> FakeAudioDriver:
        """A fresh instance of the machine's backend, holding the device list as it stands now."""
        driver = FakeAudioDriver(self, index=len(self.drivers), devices=tuple(self.devices))
        self.drivers.append(driver)
        return driver

    def occupy(self) -> None:
        """Another program takes the device, so every open is refused as busy until it lets go."""
        with self._lock:
            self._occupied = True

    def free(self) -> None:
        with self._lock:
            self._occupied = False

    def open_stream(self, call: OpenCall) -> FakeOutputStream:
        """Opens a stream on the device, refusing it as busy while the device holds one."""
        self.hooks.opening(call)
        thread = threading.current_thread().name
        with self._lock:
            if self._occupied:
                self.timeline.record(Refused(device=call.device, reason=DEVICE_BUSY, thread=thread))
                raise OSError(DEVICE_BUSY)

            if self._open:
                self.timeline.record(Violation(kind=ViolationKind.OVERLAPPING_OPEN, stream=None, thread=thread))
                self.timeline.record(Refused(device=call.device, reason=DEVICE_BUSY, thread=thread))
                raise OSError(DEVICE_BUSY)

            stream = self._next_stream
            self._next_stream += 1
            self._open.append(stream)
            self.timeline.record(
                Opened(
                    stream=stream,
                    device=call.device,
                    sample_rate=call.sample_rate,
                    frames_per_buffer=call.frames_per_buffer,
                    thread=thread,
                )
            )

        return FakeOutputStream(
            stream=stream,
            sample_rate=call.sample_rate,
            pacing=self.pacing,
            timeline=self.timeline,
            hooks=self.hooks,
            on_closed=self._release_stream,
        )

    def has_open_streams(self) -> bool:
        with self._lock:
            return bool(self._open)

    def _release_stream(self, stream: int) -> None:
        with self._lock:
            if stream in self._open:
                self._open.remove(stream)
