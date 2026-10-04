import pytest

from tests.suite.screens.boundaries.audio import OutputDevice


@pytest.fixture
def output_device() -> OutputDevice:
    """The machine offers no output device."""
    return OutputDevice.NONE
