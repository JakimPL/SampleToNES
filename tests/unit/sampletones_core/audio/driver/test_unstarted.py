from typing import Final

import pytest

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.driver import UnstartedDriver
from tests.suite.base import BaseTestSuite

DEVICE_INDEX: Final[int] = 0
SAMPLE_RATE: Final[int] = 44100


class TestAnAudioSystemThatRefusedToStart(BaseTestSuite):
    """The stand-in offers what a machine without output offers: no device, no default and no stream."""

    def test_it_lists_no_device(self) -> None:
        driver = UnstartedDriver()

        assert driver.device_count() == 0
        assert driver.default_output_index() is None

    def test_the_catalog_it_reads_as_holds_no_device_and_no_default(self) -> None:
        catalog = DeviceCatalog.read(UnstartedDriver())

        assert catalog.devices == {}
        assert catalog.default_device() is None

    def test_no_index_names_a_device(self) -> None:
        with pytest.raises(IndexError):
            UnstartedDriver().device(DEVICE_INDEX)

    def test_no_device_plays_any_rate(self) -> None:
        assert not UnstartedDriver().supports(DEVICE_INDEX, SAMPLE_RATE)

    def test_no_stream_opens(self) -> None:
        with pytest.raises(OSError):
            UnstartedDriver().open_output(device_index=DEVICE_INDEX, sample_rate=SAMPLE_RATE, frames_per_buffer=None)

    def test_it_terminates_quietly(self) -> None:
        UnstartedDriver().terminate()
