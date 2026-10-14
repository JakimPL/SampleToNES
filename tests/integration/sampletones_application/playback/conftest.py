from pathlib import Path
from typing import Dict, Generator, Iterator, Tuple

import pytest

from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from tests.integration.sampletones_application.playback.material import REALTIME_MARKER, STEPPED_MARKER
from tests.integration.sampletones_application.playback.rig import PlaybackRig, check_after
from tests.suite.application import live_queue, scheduling
from tests.suite.audio.machine import (
    HEADPHONES,
    SPEAKERS,
    FakeAudioSystem,
    FakeDevice,
    machine,
    realtime_machine,
    ticking_machine,
)
from tests.suite.audio.pacing import StepPacing

__all__ = ["live_queue", "scheduling"]

DEFAULT_DEVICE: int = 0
PASSED_CALLS: Dict[str, bool] = {}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", f"{REALTIME_MARKER}: the device plays at its own rate")
    config.addinivalue_line("markers", f"{STEPPED_MARKER}: the device takes each write when the case grants it")


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Notes whether each case's call passed, which decides how strictly the after-check speaks."""
    report = yield
    if report.when == "call":
        PASSED_CALLS[item.nodeid] = report.passed

    return report


@pytest.fixture
def devices() -> Tuple[FakeDevice, ...]:
    """The machine's devices: speakers, which the machine starts on, and headphones playing at another rate."""
    return (SPEAKERS, HEADPHONES)


@pytest.fixture
def steps() -> StepPacing:
    """The grants a stepped device waits for."""
    return StepPacing()


@pytest.fixture
def system(request: pytest.FixtureRequest, devices: Tuple[FakeDevice, ...], steps: StepPacing) -> FakeAudioSystem:
    """The machine a case plays on: faster than real time, at real time, or paced write by write."""
    if request.node.get_closest_marker(REALTIME_MARKER) is not None:
        return realtime_machine(devices, default_device=DEFAULT_DEVICE)

    if request.node.get_closest_marker(STEPPED_MARKER) is not None:
        return machine(devices, default_device=DEFAULT_DEVICE, pacing=steps)

    return ticking_machine(devices, default_device=DEFAULT_DEVICE)


@pytest.fixture
def rig(
    request: pytest.FixtureRequest,
    system: FakeAudioSystem,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    live_queue: None,
    scheduling: SchedulingBehavior,
) -> Iterator[PlaybackRig]:
    """The application's playback on the case's machine, held to the device's rules once a passing case ends."""
    playback = PlaybackRig(system, directory=tmp_path, scheduling=scheduling, monkeypatch=monkeypatch)
    yield playback
    check_after(playback, strict=PASSED_CALLS.pop(request.node.nodeid, False))
