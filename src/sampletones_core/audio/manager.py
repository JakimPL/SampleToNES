import contextlib
import os
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Generator, List, Optional, cast

import numpy as np
import pyaudio

from sampletones_core.constants.audio import (
    DEFAULT_BUFFER_SIZE,
    SAMPLE_RATES,
    BufferSize,
    SampleRate,
)
from sampletones_shared.exceptions import PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.locales import to_utf8

from .device import AudioDevice, CurrentDevice
from .io import load_audio
from .validation import validate_buffer_size, validate_sample_rate

CHANNELS = 1
FORMAT = pyaudio.paFloat32

OnPlaybackErrorCallback = Callable[[PlaybackError], None]


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


class AudioDeviceManager(CallbackMixin):
    """
    Manages audio output devices and playback of audio data.

    This class handles enumeration and configuration of audio output devices,
    manages threaded audio playback with pause/resume capabilities, and provides
    position callbacks for playback tracking. Uses PyAudio for low-level audio I/O.

    The manager uses a background thread for audio playback.
    """

    def __init__(self) -> None:
        """
        Initialize the audio device manager.

        Enumerates available audio devices, initializes the default output device,
        and sets up threading primitives for playback management.
        """
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._devices: Dict[int, AudioDevice] = {}

        self._device_index: Optional[int] = None
        self._sample_rate: Optional[SampleRate] = None
        self._buffer_size: BufferSize = DEFAULT_BUFFER_SIZE

        self._audio_data: Optional[np.ndarray] = None
        self._position: int = 0
        self._playing: bool = False
        self._active_priority: int = 0
        self._paused: bool = False
        self._stop: bool = False

        self._playback_thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()
        self._resume_event: threading.Event = threading.Event()
        self._resume_event.set()

        self._position_callback: Optional[Callable[[int], None]] = None
        self.on_playback_error: Optional[OnPlaybackErrorCallback] = None
        self.on_acquire_output: Optional[Callable[[], None]] = None
        self.external_output_priority: Optional[Callable[[], Optional[int]]] = None

        self.refresh_devices()
        self._initialize_default_device()

    def reinitialize(self) -> None:
        """
        Reinitialize the PyAudio instance.

        Creates a new PyAudio instance if none exists, or terminates the existing
        instance and creates a new one. Stops any active playback before reinitializing.
        """
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
        """
        Enumerate and refresh the list of available audio output devices.

        Queries PyAudio for all available devices, filters for output-capable devices,
        determines supported sample rates for each device, and identifies default
        input/output devices. Devices without supported sample rates are skipped.
        """
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

        self._devices = {}
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

    def _is_sample_rate_supported(
        self,
        device_index: int,
        sample_rate: int,
    ) -> bool:
        """
        Check if a device supports a specific sample rate.

        Args:
            device_index: Index of the audio device to check.
            sample_rate: Sample rate in Hz to test.

        Returns:
            True if the device supports the sample rate, False otherwise.
        """
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

    def _get_supported_sample_rates(
        self,
        device_index: int,
        default_sample_rate: int,
    ) -> List[SampleRate]:
        """
        Get list of supported sample rates for a device.

        Tests all standard sample rates plus the device's default sample rate
        to determine which rates are supported.

        Args:
            device_index: Index of the audio device to query.
            default_sample_rate: Device's default sample rate.

        Returns:
            List of supported sample rates in Hz.
        """
        supported_rates: List[SampleRate] = []
        candidate_rates = sorted(set(SAMPLE_RATES) | {default_sample_rate})
        for rate in candidate_rates:
            if self._is_sample_rate_supported(device_index, rate):
                supported_rates.append(cast(SampleRate, rate))

        return supported_rates

    def _initialize_default_device(self) -> None:
        """
        Initialize the default audio output device.

        Queries PyAudio for the system's default output device and configures
        the manager to use it with its default sample rate. If no default device
        is found, logs a warning.
        """
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
        """
        Get the currently selected audio device index.

        Returns:
            The device index.

        Raises:
            ValueError: If no audio device is currently selected.
        """
        if self._device_index is None:
            raise ValueError("No audio device selected")

        return self._device_index

    @device_index.setter
    def device_index(self, value: int) -> None:
        """
        Set the audio device by index.

        Stops any active playback and switches to the specified device,
        automatically setting the sample rate to the device's default.

        Args:
            value: Index of the device to select.

        Raises:
            ValueError: If the device index is not found.
        """
        if value not in self._devices:
            raise ValueError(f"Device with index {value} not found")

        self.stop()
        device = self._devices[value]
        self._device_index = value
        self._sample_rate = device.default_sample_rate

    @property
    def buffer_size(self) -> BufferSize:
        """
        Get the current audio buffer size in samples.

        Returns:
            Buffer size in samples.
        """
        return self._buffer_size

    @buffer_size.setter
    def buffer_size(self, value: BufferSize) -> None:
        """
        Set the audio buffer size.

        Validates the buffer size before setting.

        Args:
            value: Buffer size in samples (must be one of the valid buffer sizes).

        Raises:
            ValueError: If the buffer size is not valid.
        """
        validate_buffer_size(value)
        self._buffer_size = value

    @property
    def device_name(self) -> str:
        """
        Get the name of the currently selected audio device.

        Returns:
            Device name as a string.
        """
        return self._devices[self.device_index].name

    @property
    def sample_rate(self) -> SampleRate:
        """
        Get the currently configured sample rate.

        Returns:
            Sample rate in Hz.

        Raises:
            ValueError: If no audio device is currently selected.
        """
        if self._sample_rate is None:
            raise ValueError("No audio device selected")

        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: SampleRate) -> None:
        """
        Set the sample rate for audio playback.

        Validates the sample rate before setting and ensures
        it is supported by the current device.

        Args:
            value: Sample rate in Hz.

        Raises:
            ValueError: If the sample rate is not valid or not supported by the current device.
        """
        validate_sample_rate(value)
        device = self._devices[self.device_index]
        if value not in device.supported_sample_rates:
            raise ValueError(f"Sample rate {value} not supported by device {device.name}")

        self._sample_rate = value

    def get_current_device(self) -> CurrentDevice:
        """
        Get a snapshot of the current device configuration.

        Returns:
            CurrentDevice object containing device index, name, sample rate, and host API.
        """
        return CurrentDevice(
            device_index=self.device_index,
            name=self.device_name,
            sample_rate=self.sample_rate,
            host_api=self._devices[self.device_index].host_api,
        )

    def set_current_device(self, current_device: CurrentDevice) -> None:
        """
        Configure the manager from a CurrentDevice object.

        Attempts to find a matching device by name and host API. If found, configures
        the device with the specified sample rate. If not found, logs a warning or
        initializes the default device.

        Args:
            current_device: Device configuration to apply.
        """
        device_index = self.find_device_index(current_device)
        if device_index != -1:
            return self.configure_device(
                device_index=device_index,
                sample_rate=current_device.sample_rate,
            )

        if current_device.name:
            logger.warning(f"Audio device '{current_device.name}' not found. " f"Falling back to default device.")
        else:
            logger.info("No device specified. Initializing the default audio device.")

        return self._initialize_default_device()

    def find_device_index(
        self,
        current_device: CurrentDevice,
    ) -> int:
        """
        Find a device index matching a CurrentDevice configuration.

        Args:
            current_device: Device configuration to search for.

        Returns:
            Device index if found, -1 otherwise.
        """
        for device in self._devices.values():
            if device.name == current_device.name:
                return device.index

        return -1

    def list_devices(self) -> Dict[int, AudioDevice]:
        """
        Get all available audio output devices.

        Returns:
            Dictionary mapping device indices to AudioDevice objects.
        """
        return dict(self._devices)

    def configure_device(
        self,
        device_index: int,
        sample_rate: SampleRate,
    ) -> None:
        """
        Configure the audio device and sample rate.

        Stops any active playback and switches to the specified device and sample rate.
        If the sample rate is not supported, falls back to the first supported rate for that device.

        Args:
            device_index: Index of the device to configure.
            sample_rate: Desired sample rate in Hz.

        Raises:
            ValueError: If the device index is not found.
        """
        if device_index not in self._devices:
            raise ValueError(f"Device with index {device_index} not found")

        device = self._devices[device_index]
        if sample_rate not in device.supported_sample_rates:
            fallback_rate = device.supported_sample_rates[0]
            logger.warning(
                f"Sample rate {sample_rate} not supported by device {device.name}. " f"Falling back to {fallback_rate}"
            )
            sample_rate = fallback_rate

        self.stop()
        self.device_index = device_index
        self.sample_rate = sample_rate
        logger.info(f"Audio device configured: '{self.device_name}' (index={device_index}, sample_rate={sample_rate})")

    def set_buffer_size(self, buffer_size: BufferSize) -> None:
        """
        Set the audio buffer size with logging.

        Args:
            buffer_size: Buffer size in samples.
        """
        self.buffer_size = buffer_size
        logger.info(f"Audio buffer size set to {buffer_size} samples")

    def set_position_callback(self, callback: Optional[Callable[[int], None]]) -> None:
        """
        Register a callback for playback position updates.

        The callback is invoked during playback with the current position in samples.

        Args:
            callback: Function to call with position updates, or None to clear.
        """
        self.set_callbacks(_position_callback=callback)

    def set_position(self, position: int) -> None:
        """
        Seek to a specific position in the audio.

        The position is clamped to valid range [0, audio_length].

        Args:
            position: Target position in samples.
        """
        with self._lock:
            if self._audio_data is not None:
                self._position = max(0, min(position, len(self._audio_data)))

    def play_file(
        self,
        filepath: Path,
        *,
        update: bool = True,
        priority: int = 0,
    ) -> None:
        """
        Load and play an audio file.

        Args:
            filepath: Path to the audio file.
            update: If True, invoke position callback during playback.
            priority: Output-request priority; see :meth:`play`.
        """
        audio = load_audio(filepath, normalize=False, quantize=False)
        self.play(audio, update=update, priority=priority)

    def play(
        self,
        audio: np.ndarray,
        *,
        update: bool = True,
        priority: int = 0,
    ) -> None:
        """
        Play audio data.

        Starts playing the provided audio data in a background thread, after stopping
        any active playback.

        The output device exposes a single stream, so requests are ranked by ``priority``:
        this request is skipped when output is already held at a strictly higher priority
        (a buffer of this manager, or an external stream reported by ``external_output_priority``).
        Otherwise it takes over, releasing any external stream first via ``on_acquire_output``.

        Args:
            audio: Audio data as numpy array (will be converted to float32).
            update: If True, invoke position callback during playback.
            priority: Output-request priority; higher wins. Callers assign the meaning.
        """
        external_priority = self.call(self.external_output_priority)
        with self._lock:
            internal_priority = self._active_priority if self._playing else None

        held = max(
            (priority for priority in (internal_priority, external_priority) if priority is not None), default=None
        )
        if held is not None and priority < held:
            return

        self.stop()
        if external_priority is not None:
            self.call(self.on_acquire_output)

        with self._lock:
            self._audio_data = audio.astype(np.float32)
            self._position = 0
            self._playing = True
            self._active_priority = priority
            self._paused = False
            self._stop = False

        self._resume_event.set()
        self._playback_thread = threading.Thread(
            target=self._playback_worker,
            kwargs={"update": update},
            daemon=True,
            name="AudioPlaybackWorker",
        )

        self._playback_thread.start()

    def _playback_loop(self, stream: pyaudio.Stream, update: bool) -> None:
        """
        Internal audio playback loop.

        Continuously reads audio chunks and writes them to the stream until stopped,
        paused, or audio ends. Respects pause state and stop flag.

        Args:
            stream: PyAudio stream to write audio data to.
            update: If True, invoke position callback after each chunk.
        """
        while True:
            self._resume_event.wait(timeout=0.1)

            with self._lock:
                if self._stop or self._audio_data is None:
                    break

                if self._paused:
                    continue

                remaining = len(self._audio_data) - self._position
                if remaining <= 0:
                    break

                chunk_size = min(self._buffer_size, remaining)
                chunk = self._audio_data[self._position : self._position + chunk_size]
                self._position += chunk_size
                current_position = self._position

            stream.write(chunk.tobytes())

            if update and self._position_callback is not None:
                self.call(self._position_callback, current_position)

    def _playback_worker(self, *, update: bool = True) -> None:
        """
        Playback thread worker function.

        Opens an audio stream, runs the playback loop, and ensures cleanup.
        Handles stream opening errors by invoking the error callback.

        Args:
            update: If True, invoke position callback during playback.
        """
        assert self._pyaudio is not None, "PyAudio instance is not initialized"
        logger.debug(f"Starting playback: device_index={self._device_index}, sample_rate={self._sample_rate}")
        try:
            stream = self._pyaudio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=self.sample_rate,
                output=True,
                output_device_index=self._device_index,
            )
        except OSError as exception:
            playback_error = PlaybackError(f"Failed to open audio stream: {exception}")
            self.call(self.on_playback_error, playback_error)
            raise playback_error from exception

        try:
            self._playback_loop(stream, update)
        finally:
            stream.stop_stream()
            stream.close()
            self._reset(update=update)

    def _reset(self, *, update: bool = True) -> None:
        """
        Reset playback state to idle.

        Clears playing/paused flags, resets position, and releases audio data.
        Optionally invokes position callback with position 0.

        Args:
            update: If True, invoke position callback with 0.
        """
        with self._lock:
            self._playing = False
            self._paused = False
            self._position = 0
            self._audio_data = None

        if update and self._position_callback is not None:
            self.call(self._position_callback, 0)

    def pause(self) -> None:
        """
        Pause playback.

        Playback can be resumed by calling resume().
        Audio position is preserved.
        """
        with self._lock:
            self._paused = True

        self._resume_event.clear()

    def resume(self) -> None:
        """
        Resume paused playback.

        Continues playback from the current position.
        """
        with self._lock:
            self._paused = False

        self._resume_event.set()

    def stop(self) -> None:
        """
        Stop playback and reset state.

        Signals the playback thread to stop, waits for it to terminate (up to 1 second),
        and resets all playback state.
        """
        with self._lock:
            self._stop = True

        self._resume_event.set()
        if self._playback_thread is not None:
            self._playback_thread.join(timeout=1.0)

        self._playback_thread = None
        self._reset()

    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.

        Returns:
            True if playing (including when paused), False otherwise.
        """
        with self._lock:
            return self._playing

    def is_paused(self) -> bool:
        """
        Check if playback is currently paused.

        Returns:
            True if paused, False otherwise.
        """
        with self._lock:
            return self._paused

    def open_output_stream(
        self,
        *,
        sample_rate: int,
        buffer_size: int,
    ) -> pyaudio.Stream:
        """Open a blocking output stream for caller-managed streaming playback.

        The caller owns the stream's lifetime and must close it when done. Any buffer
        playback owned by this manager is stopped first, since the output device allows
        only a single open stream at a time.

        Args:
            sample_rate: Sample rate in Hz.
            buffer_size: Frames per buffer (controls write granularity).

        Raises:
            PlaybackError: If PyAudio is not initialized.
        """
        if self._pyaudio is None:
            raise PlaybackError("PyAudio not initialized; call reinitialize() first")

        self.stop()
        return self._pyaudio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=sample_rate,
            output=True,
            output_device_index=self._device_index,
            frames_per_buffer=buffer_size,
        )

    def terminate(self) -> None:
        """
        Clean up and terminate the audio device manager.

        Stops any active playback and terminates the PyAudio instance.
        Should be called when the manager is no longer needed.
        """
        if self._pyaudio is not None:
            self.stop()
            self._pyaudio.terminate()
            self._pyaudio = None
