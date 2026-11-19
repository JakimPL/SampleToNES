import pytest

from automation.boundaries.audio import OutputDevice


@pytest.fixture
def output_device() -> OutputDevice:
    """The machine's audio system refuses to start."""
    return OutputDevice.UNSTARTED
