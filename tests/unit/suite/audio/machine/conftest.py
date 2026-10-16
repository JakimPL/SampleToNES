import pytest

from tests.suite.audio.machine import HEADPHONES, MICROPHONE, SPEAKERS, FakeAudioSystem, ticking_machine


@pytest.fixture(name="system")
def system_fixture() -> FakeAudioSystem:
    """A machine with a pair of speakers as its default device, headphones, and a microphone."""
    return ticking_machine([SPEAKERS, HEADPHONES, MICROPHONE], default_device=0)
