from typing import Dict, Optional

from sampletones_core.constants.audio import (
    DEFAULT_BUFFER_SIZE,
    BufferSize,
    SampleRate,
)
from sampletones_shared.logger import logger

from .catalog import DeviceCatalog
from .device import AudioDevice, CurrentDevice
from .output.settings import OutputSettings
from .validation import validate_buffer_size


class AudioDeviceManager:
    """The output devices the backend lists and the one the reader chose to play on, with its rate and buffer size.

    The manager is the render thread's view of the devices: the Audio settings dialog reads it and the
    reader's choice lands in it. The audio output plays on the settings it answers, and a refresh hands it
    the catalog the renewed backend lists, where the chosen device is found again by its name.
    """

    def __init__(self, catalog: DeviceCatalog) -> None:
        """Takes the devices the backend lists, with the system's default device in force.

        Args:
            catalog: The devices the backend listed as it started.
        """
        self._catalog = catalog
        self._device: Optional[CurrentDevice] = catalog.default_device()
        self._buffer_size: BufferSize = DEFAULT_BUFFER_SIZE
        if self._device is None:
            logger.warning("No default output device found")

    @property
    def buffer_size(self) -> BufferSize:
        return self._buffer_size

    @property
    def settings(self) -> OutputSettings:
        """The device, rate and buffer size the output plays on."""
        return OutputSettings(device=self._device, buffer_size=self._buffer_size)

    def adopt(self, catalog: DeviceCatalog) -> None:
        """Takes the devices a refreshed backend lists, finding the device in force again by its name.

        A device the refresh took off the list leaves no device in force, until the reader chooses another.
        """
        self._catalog = catalog
        if self._device is not None:
            self._device = catalog.locate(self._device)

    def get_current_device(self) -> Optional[CurrentDevice]:
        """The device in force and the rate it plays at, or ``None`` while no listed device is chosen."""
        return self._device

    def list_devices(self) -> Dict[int, AudioDevice]:
        return dict(self._catalog.devices)

    def set_current_device(self, current_device: CurrentDevice) -> None:
        """Takes the device a saved session names, found by its name, or the system's default where it is missing."""
        located = self._catalog.locate(current_device)
        if located is not None:
            self._device = located
            return

        if current_device.name:
            logger.warning(f"Audio device '{current_device.name}' not found. Falling back to default device.")
        else:
            logger.info("No device specified. Initializing the default audio device.")

        self._device = self._catalog.default_device()

    def configure_device(self, device_index: int, sample_rate: SampleRate) -> CurrentDevice:
        """Takes the device and rate the reader chose, falling back to a rate the device plays.

        Returns:
            CurrentDevice: The device and the rate now in force.

        Raises:
            ValueError: If no listed device stands at ``device_index``.
        """
        self._device = self._catalog.configured(device_index, sample_rate)
        logger.info(
            f"Audio device configured: '{self._device.name}' (index={device_index}, "
            f"sample_rate={self._device.sample_rate})"
        )
        return self._device

    def set_buffer_size(self, buffer_size: BufferSize) -> None:
        """Takes the frames the device is handed per buffer.

        Raises:
            ValueError: If ``buffer_size`` is not one the application offers.
        """
        validate_buffer_size(buffer_size)
        self._buffer_size = buffer_size
        logger.info(f"Audio buffer size set to {buffer_size} samples")
