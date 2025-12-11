import contextlib
import os
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Generator, List, Optional, cast

import numpy as np
import pyaudio

from sampletones.audio import load_audio
from sampletones.exceptions import PlaybackError
from sampletones.utils import to_utf8
from sampletones.utils.logger import logger

from .device import SAMPLE_RATES, AudioDevice, CurrentDevice, SampleRate

CHANNELS = 1
FORMAT = pyaudio.paFloat32
CHUNK_SIZE = 1024


@contextlib.contextmanager
def _capture_stderr_to_logger() -> Generator[None, None, None]:
    stderr_fd = sys.stderr.fileno()
    original_stderr_fd = os.dup(stderr_fd)

    read_pipe, write_pipe = os.pipe()
    os.dup2(write_pipe, stderr_fd)

    try:
        yield
    finally:
        os.dup2(original_stderr_fd, stderr_fd)
        os.close(original_stderr_fd)
        os.close(write_pipe)

        os.set_blocking(read_pipe, False)
        try:
            captured = os.read(read_pipe, 65536).decode("utf-8", errors="replace")
        except BlockingIOError:
            captured = ""
        os.close(read_pipe)

        for line in captured.strip().splitlines():
            if line.strip():
                line = line.replace("ALSA lib ", "")
                logger.warning(f"ALSA: {line.strip()}")


class AudioDeviceManager:
    def __init__(self) -> None:
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._devices: Dict[int, AudioDevice] = {}

        self._device_index: Optional[int] = None
        self._sample_rate: Optional[SampleRate] = None

        self._audio_data: Optional[np.ndarray] = None
        self._position: int = 0
        self._playing: bool = False
        self._paused: bool = False
        self._position_callback: Optional[Callable[[int], None]] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_flag: bool = False

        self.refresh_devices()
        self._initialize_default_device()

    def reinitialize(self) -> None:
        with _capture_stderr_to_logger():
            if self._pyaudio is None:
                self._pyaudio = pyaudio.PyAudio()
                logger.debug("AudioDeviceManager initialized")
                return

            self.stop()
            self._pyaudio.terminate()
            self._pyaudio = pyaudio.PyAudio()
            logger.debug("AudioDeviceManager reinitialized")

    def refresh_devices(self) -> None:
        self.reinitialize()
        assert self._pyaudio is not None, "PyAudio instance is not initialized"

        try:
            default_input_index = int(self._pyaudio.get_default_input_device_info()["index"])
        except IOError:
            default_input_index = -1

        try:
            default_output_index = int(self._pyaudio.get_default_output_device_info()["index"])
        except IOError:
            default_output_index = -1

        self._devices: Dict[int, AudioDevice] = {}
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if int(info["maxOutputChannels"]) == 0:
                continue

            device_name = to_utf8(str(info["name"]))
            default_sample_rate: int = int(info["defaultSampleRate"])
            if default_sample_rate not in SAMPLE_RATES:
                logger.warning(f"Device '{device_name}' has an uncommon default sample rate {default_sample_rate}")

            supported_rates = self._get_supported_sample_rates(i, default_sample_rate)
            if not supported_rates:
                logger.warning(f"Device '{device_name}' has no supported sample rates, skipping")
                continue

            host_api = int(info["hostApi"])
            self._devices[i] = AudioDevice(
                index=i,
                name=device_name,
                is_input=int(info["maxInputChannels"]) > 0,
                is_output=True,
                is_default_input=i == default_input_index,
                is_default_output=i == default_output_index,
                default_sample_rate=cast(SampleRate, default_sample_rate),
                supported_sample_rates=supported_rates,
                host_api=host_api,
            )

    def _is_sample_rate_supported(self, device_index: int, sample_rate: int) -> bool:
        assert self._pyaudio is not None, "PyAudio instance is not initialized"
        try:
            self._pyaudio.is_format_supported(
                rate=sample_rate,
                output_device=device_index,
                output_channels=CHANNELS,
                output_format=FORMAT,
            )
            return True
        except ValueError:
            return False

    def _get_supported_sample_rates(self, device_index: int, default_sample_rate: int) -> List[SampleRate]:
        supported_rates: List[SampleRate] = []
        candidate_rates = sorted(set(SAMPLE_RATES) | {default_sample_rate})
        for rate in candidate_rates:
            if self._is_sample_rate_supported(device_index, rate):
                supported_rates.append(cast(SampleRate, rate))

        return supported_rates

    def _initialize_default_device(self) -> None:
        assert self._pyaudio is not None, "PyAudio instance is not initialized"
        try:
            info = self._pyaudio.get_default_output_device_info()
            device_index = int(info["index"])
            if device_index in self._devices:
                device = self._devices[device_index]
                self._device_index = device_index
                self._sample_rate = device.default_sample_rate
        except IOError:
            logger.warning("No default output device found")

    @property
    def device_index(self) -> int:
        if self._device_index is None:
            raise ValueError("No audio device selected")

        return self._device_index

    @device_index.setter
    def device_index(self, value: int) -> None:
        if value not in self._devices:
            raise ValueError(f"Device with index {value} not found")

        self.stop()
        device = self._devices[value]
        self._device_index = value
        self._sample_rate = device.default_sample_rate

    @property
    def device_name(self) -> str:
        return self._devices[self.device_index].name

    @property
    def sample_rate(self) -> SampleRate:
        if self._sample_rate is None:
            raise ValueError("No audio device selected")

        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: SampleRate) -> None:
        if not value in SAMPLE_RATES:
            raise ValueError(f"Sample rate {value} is not valid")

        device = self._devices[self.device_index]
        if value not in device.supported_sample_rates:
            raise ValueError(f"Sample rate {value} not supported by device {device.name}")

        self._sample_rate = value

    def get_current_device(self) -> CurrentDevice:
        return CurrentDevice(
            device_index=self.device_index,
            name=self.device_name,
            sample_rate=self.sample_rate,
            host_api=self._devices[self.device_index].host_api,
        )

    def set_current_device(self, current_device: CurrentDevice) -> None:
        device_index = self.find_device_index(current_device)
        if device_index != -1:
            return self.configure_device(
                device_index=current_device.device_index,
                sample_rate=current_device.sample_rate,
            )

        logger.warning(f"Audio device '{current_device.name}' not found. Cannot set current device.")
        return None

    def find_device_index(self, current_device: CurrentDevice) -> int:
        for device in self._devices.values():
            if device.name == current_device.name and current_device.host_api == device.host_api:
                return device.index

        return -1

    def list_devices(self) -> Dict[int, AudioDevice]:
        return dict(self._devices)

    def configure_device(self, device_index: int, sample_rate: SampleRate) -> None:
        if device_index not in self._devices:
            logger.error(f"Audio device with index {device_index} not found")
            return

        device = self._devices[device_index]
        if sample_rate not in device.supported_sample_rates:
            fallback_rate = device.default_sample_rate
            logger.warning(
                f"Sample rate {sample_rate} not supported by device {device.name}. " f"Falling back to {fallback_rate}"
            )
            sample_rate = fallback_rate

        self.stop()
        self.device_index = device_index
        self.sample_rate = sample_rate
        logger.info(f"Audio device configured: {self.device_name} (index={device_index}, sample_rate={sample_rate})")

    def set_position_callback(self, callback: Optional[Callable[[int], None]]) -> None:
        self._position_callback = callback

    def set_position(self, position: int) -> None:
        if self._audio_data is not None:
            self._position = max(0, min(position, len(self._audio_data)))

    def play_file(self, filepath: Path) -> None:
        audio = load_audio(filepath, normalize=False, quantize=False)
        self.play(audio)

    def play(self, audio: np.ndarray) -> None:
        self.stop()
        self._audio_data = audio.astype(np.float32)
        self._position = 0
        self._playing = True
        self._paused = False
        self._stop_flag = False
        self._playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self._playback_thread.start()

    def _playback_worker(self) -> None:
        assert self._pyaudio is not None, "PyAudio instance is not initialized"
        try:
            stream = self._pyaudio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=self.sample_rate,
                output=True,
                output_device_index=self._device_index,
            )
        except OSError as exception:
            raise PlaybackError(f"Failed to open audio stream: {exception}") from exception

        while not self._stop_flag and self._audio_data is not None:
            if self._paused:
                continue

            remaining = len(self._audio_data) - self._position
            if remaining <= 0:
                break

            chunk_size = min(CHUNK_SIZE, remaining)
            chunk = self._audio_data[self._position : self._position + chunk_size]
            stream.write(chunk.tobytes())
            self._position += chunk_size

            if self._position_callback:
                self._position_callback(self._position)

        stream.stop_stream()
        stream.close()
        self._reset()

    def _reset(self) -> None:
        self._playing = False
        self._paused = False
        self._position = 0
        self._audio_data = None

        if self._position_callback:
            self._position_callback(0)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._stop_flag = True
        if self._playback_thread is not None:
            self._playback_thread.join(timeout=1.0)

        self._playback_thread = None
        self._reset()

    def is_playing(self) -> bool:
        return self._playing

    def is_paused(self) -> bool:
        return self._paused

    def terminate(self) -> None:
        if self._pyaudio is not None:
            self.stop()
            self._pyaudio.terminate()
            self._pyaudio = None
