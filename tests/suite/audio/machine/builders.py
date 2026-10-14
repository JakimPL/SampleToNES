from typing import Final, Optional, Sequence

from tests.suite.audio.pacing import Pacing, StepPacing, TickerPacing
from tests.suite.audio.timeline import Timeline

from .device import FakeDevice
from .system import FakeAudioSystem

TICKER_SPEED: Final[float] = 50.0
TICKER_BUFFER_SECONDS: Final[float] = 0.05


def machine(devices: Sequence[FakeDevice], *, default_device: Optional[int], pacing: Pacing) -> FakeAudioSystem:
    """A fake machine whose devices are ``devices``, paced by ``pacing`` and recorded on a timeline of its own."""
    return FakeAudioSystem(devices, default_device=default_device, pacing=pacing, timeline=Timeline())


def ticking_machine(devices: Sequence[FakeDevice], *, default_device: Optional[int]) -> FakeAudioSystem:
    """A fake machine whose device plays faster than real time, for a case reading outcomes alone."""
    return machine(
        devices,
        default_device=default_device,
        pacing=TickerPacing(speed=TICKER_SPEED, buffer_seconds=TICKER_BUFFER_SECONDS),
    )


def stepped_machine(devices: Sequence[FakeDevice], *, default_device: Optional[int]) -> FakeAudioSystem:
    """A fake machine whose device takes each write only when the case grants it."""
    return machine(devices, default_device=default_device, pacing=StepPacing())
