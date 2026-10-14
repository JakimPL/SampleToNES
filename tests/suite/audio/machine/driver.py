from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional, Tuple

from sampletones_core.audio.driver import DriverDevice
from tests.suite.audio.timeline import Terminated, Violation, ViolationKind

from .calls import OpenCall
from .device import FakeDevice
from .messages import BACKEND_TERMINATED, INVALID_DEVICE
from .stream import FakeOutputStream

if TYPE_CHECKING:
    from .system import FakeAudioSystem


class FakeAudioDriver:
    """One instance of the fake machine's backend, holding the device list it was created with.

    It answers the calls the device manager makes, as PortAudio does: the devices it was created with, the
    rates each one plays, and streams on them. A call after it was terminated is a violation, and so is
    terminating it while a stream is still open.
    """

    def __init__(self, system: FakeAudioSystem, *, index: int, devices: Tuple[FakeDevice, ...]) -> None:
        self.system = system
        self.index = index
        self._devices = devices
        self.terminated: bool = False

    def device_count(self) -> int:
        self._check_alive()
        return len(self._devices)

    def device(self, index: int) -> DriverDevice:
        self._check_alive()
        device = self._devices[index]
        return DriverDevice(
            index=index,
            name=device.name,
            max_output_channels=device.output_channels,
            default_sample_rate=device.default_sample_rate,
            host_api=device.host_api,
        )

    def default_output_index(self) -> Optional[int]:
        self._check_alive()
        return self.system.default_device

    def supports(self, index: int, sample_rate: int) -> bool:
        self._check_alive()
        return sample_rate in self._devices[index].supported_sample_rates

    def open_output(
        self,
        *,
        device_index: int,
        sample_rate: int,
        frames_per_buffer: Optional[int],
    ) -> FakeOutputStream:
        self._check_alive()
        if not 0 <= device_index < len(self._devices):
            raise OSError(INVALID_DEVICE)

        return self.system.open_stream(
            OpenCall(device=device_index, sample_rate=sample_rate, frames_per_buffer=frames_per_buffer)
        )

    def terminate(self) -> None:
        self._check_alive()
        thread = threading.current_thread().name
        if self.system.has_open_streams():
            self.system.timeline.record(
                Violation(kind=ViolationKind.TERMINATE_WITH_OPEN_STREAM, stream=None, thread=thread)
            )

        self.terminated = True
        self.system.timeline.record(Terminated(driver=self.index, thread=thread))

    def _check_alive(self) -> None:
        if self.terminated:
            thread = threading.current_thread().name
            self.system.timeline.record(Violation(kind=ViolationKind.USE_AFTER_TERMINATE, stream=None, thread=thread))
            raise OSError(BACKEND_TERMINATED)
