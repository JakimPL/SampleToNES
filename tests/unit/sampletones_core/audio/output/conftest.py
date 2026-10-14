import contextlib
from typing import Final, Iterator

import pytest

from sampletones_core.audio.output import AudioOutput, OutputSettings
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE
from tests.suite.audio.machine import HEADPHONES, SPEAKERS, FakeAudioSystem, machine, realtime_machine, ticking_machine
from tests.suite.audio.pacing import StepPacing
from tests.unit.sampletones_core.audio.output.harness import QueuedPost, RecordingListener

SPEAKERS_INDEX: Final[int] = 0
HEADPHONES_INDEX: Final[int] = 1
CLOSE_SECONDS: Final[float] = 5.0


@contextlib.contextmanager
def _started(system: FakeAudioSystem, post: QueuedPost) -> Iterator[AudioOutput]:
    """An output on ``system`` playing through its default device, closed once the case is done with it."""
    output = AudioOutput(system.driver, post=post)
    output.configure(OutputSettings(device=output.catalog.default_device(), buffer_size=DEFAULT_BUFFER_SIZE))
    try:
        yield output
    finally:
        output.close(deadline_seconds=CLOSE_SECONDS)


@pytest.fixture
def post() -> QueuedPost:
    """The owner's thread, which a case drains."""
    return QueuedPost()


@pytest.fixture
def system() -> FakeAudioSystem:
    """A machine whose speakers are its default device and whose headphones play at another rate, faster than
    real time."""
    return ticking_machine((SPEAKERS, HEADPHONES), default_device=SPEAKERS_INDEX)


@pytest.fixture
def realtime_system() -> FakeAudioSystem:
    """The same machine, playing at its own rate, for a case acting on a sound while it plays."""
    return realtime_machine((SPEAKERS, HEADPHONES), default_device=SPEAKERS_INDEX)


@pytest.fixture
def steps() -> StepPacing:
    return StepPacing()


@pytest.fixture
def stepped_system(steps: StepPacing) -> FakeAudioSystem:
    """The same machine, taking each write only once the case grants it."""
    return machine((SPEAKERS, HEADPHONES), default_device=SPEAKERS_INDEX, pacing=steps)


@pytest.fixture
def output(system: FakeAudioSystem, post: QueuedPost) -> Iterator[AudioOutput]:
    with _started(system, post) as started:
        yield started


@pytest.fixture
def realtime_output(realtime_system: FakeAudioSystem, post: QueuedPost) -> Iterator[AudioOutput]:
    with _started(realtime_system, post) as started:
        yield started


@pytest.fixture
def stepped_output(stepped_system: FakeAudioSystem, steps: StepPacing, post: QueuedPost) -> Iterator[AudioOutput]:
    with _started(stepped_system, post) as started:
        yield started
        steps.grant(len(stepped_system.timeline.events()) + 1_000_000)


@pytest.fixture
def listener(system: FakeAudioSystem) -> RecordingListener[int]:
    return RecordingListener(streams_open=system.has_open_streams)


@pytest.fixture
def realtime_listener(realtime_system: FakeAudioSystem) -> RecordingListener[int]:
    return RecordingListener(streams_open=realtime_system.has_open_streams)


@pytest.fixture
def stepped_listener(stepped_system: FakeAudioSystem) -> RecordingListener[int]:
    return RecordingListener(streams_open=stepped_system.has_open_streams)
