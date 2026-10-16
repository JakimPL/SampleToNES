from dataclasses import dataclass
from typing import List, Mapping, Optional, Self, cast

from sampletones_core.constants.audio import SAMPLE_RATES, SampleRate
from sampletones_shared.logger import logger

from .device import AudioDevice, CurrentDevice
from .driver import AudioDriverProtocol


@dataclass(frozen=True)
class DeviceCatalog:
    """The output devices one instance of the backend lists, each with the rates it plays, and the system's default.

    A device index holds for the backend instance that listed it, so a refresh reads a new catalog from the
    renewed backend, and a device chosen before it is found again by its name.

    Attributes:
        devices: Every device that plays output at a rate the application offers, by index.
        default_index: The index of the device the system plays through by default, or ``None`` where it
            names none.
    """

    devices: Mapping[int, AudioDevice]
    default_index: Optional[int]

    @classmethod
    def read(cls, driver: AudioDriverProtocol) -> Self:
        """Lists the devices ``driver`` offers for output, keeping each one that plays at an offered rate."""
        devices = {}
        for index in range(driver.device_count()):
            device = cls._read_device(driver, index)
            if device is not None:
                devices[index] = device

        return cls(devices=devices, default_index=driver.default_output_index())

    def default_device(self) -> Optional[CurrentDevice]:
        """The system's default device at its default rate, where the catalog lists it."""
        if self.default_index is None or self.default_index not in self.devices:
            return None

        device = self.devices[self.default_index]
        return CurrentDevice.from_device(device, device.default_sample_rate)

    def configured(self, index: int, sample_rate: SampleRate) -> CurrentDevice:
        """The device at ``index`` playing at ``sample_rate``, or at the first rate it offers where it plays another.

        Raises:
            ValueError: If the catalog lists no device at ``index``.
        """
        device = self.devices.get(index)
        if device is None:
            raise ValueError(f"Device with index {index} not found")

        if sample_rate in device.supported_sample_rates:
            return CurrentDevice.from_device(device, sample_rate)

        fallback_rate = device.supported_sample_rates[0]
        logger.warning(
            f"Sample rate {sample_rate} not supported by device {device.name}. Falling back to {fallback_rate}"
        )
        return CurrentDevice.from_device(device, fallback_rate)

    def locate(self, current_device: CurrentDevice) -> Optional[CurrentDevice]:
        """The listed device bearing ``current_device``'s name, at its rate where the device still plays it.

        Returns:
            Optional[CurrentDevice]: The device found again, or ``None`` where no listed device bears the name.
        """
        index = self.find(current_device.name)
        if index is None:
            return None

        return self.configured(index, current_device.sample_rate)

    def find(self, name: str) -> Optional[int]:
        """The index of the listed device bearing ``name``, or ``None`` where none does."""
        for device in self.devices.values():
            if device.name == name:
                return device.index

        return None

    @classmethod
    def _read_device(cls, driver: AudioDriverProtocol, index: int) -> Optional[AudioDevice]:
        """The device at ``index`` with the rates it plays, or ``None`` where it plays no output at an offered rate."""
        device = driver.device(index)
        if not device.plays_output:
            return None

        if device.default_sample_rate not in SAMPLE_RATES:
            logger.warning(f"Device '{device.name}' has an uncommon default sample rate {device.default_sample_rate}")

        supported_rates = cls._supported_rates(driver, index, device.default_sample_rate)
        if not supported_rates:
            logger.warning(f"Device '{device.name}' has no supported sample rates, skipping")
            return None

        return AudioDevice(
            index=index,
            name=device.name,
            default_sample_rate=cast(SampleRate, device.default_sample_rate),
            supported_sample_rates=supported_rates,
            host_api=device.host_api,
        )

    @staticmethod
    def _supported_rates(driver: AudioDriverProtocol, index: int, default_sample_rate: int) -> List[SampleRate]:
        """The offered rates and the device's own default that the device at ``index`` plays."""
        candidate_rates = sorted(set(SAMPLE_RATES) | {default_sample_rate})
        return [cast(SampleRate, rate) for rate in candidate_rates if driver.supports(index, rate)]
