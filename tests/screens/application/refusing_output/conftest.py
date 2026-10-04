import pytest

from tests.suite.screens.boundaries.audio import OutputDevice


@pytest.fixture
def output_device() -> OutputDevice:
    """The machine offers a device that refuses every stream opened on it."""
    return OutputDevice.REFUSING
