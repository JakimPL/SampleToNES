from typing import Optional

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.driver import (
    AudioDriverFactory,
    AudioDriverProtocol,
)
from sampletones_shared.exceptions import PlaybackError


class AudioBackend:
    """The one instance of the audio backend, created through the factory the output was given.

    The thread writing to the device opens every stream on it and renews it for a refresh, and a teardown
    terminates it once that thread has ended, so one thread reaches it at a time. A renewed backend lists
    the devices as they stand, which is what a refresh reads.
    """

    def __init__(self, factory: AudioDriverFactory) -> None:
        self._factory = factory
        self._driver: Optional[AudioDriverProtocol] = factory()

    @property
    def driver(self) -> AudioDriverProtocol:
        """The instance in force.

        Raises:
            PlaybackError: If the backend was terminated.
        """
        if self._driver is None:
            raise PlaybackError("The audio backend is terminated")

        return self._driver

    def renew(self) -> DeviceCatalog:
        """Terminates the instance in force and starts the next, answering the devices the new one lists."""
        self.terminate()
        self._driver = self._factory()
        return DeviceCatalog.read(self._driver)

    def terminate(self) -> None:
        driver, self._driver = self._driver, None
        if driver is not None:
            driver.terminate()
