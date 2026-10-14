import contextlib
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Final, Generator, List, Optional, cast

import numpy as np

from sampletones_core.constants.audio import (
    DEFAULT_BUFFER_SIZE,
    SAMPLE_RATES,
    START_OF_AUDIO,
    BufferSize,
    SampleRate,
)
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

from .device import AudioDevice, CurrentDevice
from .driver import (
    AudioDriverFactory,
    AudioDriverProtocol,
    OutputStreamProtocol,
)
from .io import load_audio
from .lease import OutputLease
from .stream import close_stream, write_to_stream
from .validation import validate_buffer_size, validate_sample_rate

STOP_JOIN_SECONDS: Final[float] = 1.0
LET_GO_JOIN_SECONDS: Final[float] = 2.0

OnPlaybackErrorCallback = Callable[[PlaybackError], None]


class AudioDeviceManager(CallbackMixin):
    """
    Manages audio output devices and playback of audio data.

    This class handles enumeration and configuration of audio output devices,
    manages threaded audio playback with pause/resume capabilities, and provides
    position callbacks for playback tracking. The audio backend is reached through a driver,
    which the manager creates from ``driver_factory`` each time it starts the backend afresh.

    The manager uses a background thread for audio playback.
    """

    def __init__(self, driver_factory: AudioDriverFactory) -> None:
        """
        Initialize the audio device manager.

        Enumerates available audio devices, initializes the default output device,
        and sets up threading primitives for playback management.

        Args:
            driver_factory: Creates the driver the backend is reached through.
        """
        self._driver_factory = driver_factory
        self._driver: Optional[AudioDriverProtocol] = None
        self._devices: Dict[int, AudioDevice] = {}

        self._device_index: Optional[int] = None
        self._sample_rate: Optional[SampleRate] = None
        self._buffer_size: BufferSize = DEFAULT_BUFFER_SIZE

        self._audio_data: Optional[np.ndarray] = None
        self._position: int = 0
        self._playing: bool = False
        self._output_owner: Optional[Any] = None
        self._active_priority: int = 0
        self._paused: bool = False
        self._stop: bool = False
        self._generation: int = 0

        self._playback_thread: Optional[threading.Thread] = None
        self._let_go_workers: List[threading.Thread] = []
        self._claims: List[OutputLease] = []
        self._outstanding: List[OutputLease] = []
        self._output_closed: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._resume_event: threading.Event = threading.Event()
        self._resume_event.set()

        self._position_callback: Optional[Callable[[int], None]] = None
        self.on_playback_error: Optional[OnPlaybackErrorCallback] = None

        self.refresh_devices()
        self._initialize_default_device()

    def reinitialize(self) -> None:
        """
        Reinitialize the audio backend.

        Creates a driver if none exists, or terminates the existing one and creates
        the next. Active playback is stopped and every lease is
        released first, since terminating closes any stream still open while its holder
        writes to it. A worker a stop let go of is waited for too, since it may still be
        opening its stream. Every claim on the output is declined while the instance is
        replaced.

        Raises:
            PlaybackError: If a stream is still open after its holder was asked to release
                it, or a worker a stop let go of outlives the wait, which leaves the running
                instance in place.
        """
        if self._driver is None:
            self._driver = self._driver_factory()
            with self._lock:
                self._output_closed = False

            logger.debug("AudioDeviceManager initialized")
            return

        with self._output_held_closed():
            self.stop()
            if not self._release_every_lease():
                raise PlaybackError("An output stream is still held; the audio backend stays as it is")

            if not self._join_let_go_workers():
                raise PlaybackError("A playback worker still reaches into the audio backend; it stays as it is")

            self._driver.terminate()
            self._driver = self._driver_factory()
            logger.debug("AudioDeviceManager reinitialized")

    def refresh_devices(self) -> None:
        """
        Enumerate and refresh the list of available audio output devices.

        Queries the driver for all available devices, filters for output-capable devices,
        and determines supported sample rates for each device. Only devices with
        supported sample rates are kept.
        """
        self.reinitialize()
        driver = self._require_driver()

        self._devices = {}
        for index in range(driver.device_count()):
            device = driver.device(index)
            if not device.plays_output:
                continue

            if device.default_sample_rate not in SAMPLE_RATES:
                logger.warning(
                    f"Device '{device.name}' has an uncommon default sample rate {device.default_sample_rate}"
                )

            supported_rates = self._get_supported_sample_rates(index, device.default_sample_rate)
            if not supported_rates:
                logger.warning(f"Device '{device.name}' has no supported sample rates, skipping")
                continue

            self._devices[index] = AudioDevice(
                index=index,
                name=device.name,
                default_sample_rate=cast(SampleRate, device.default_sample_rate),
                supported_sample_rates=supported_rates,
                host_api=device.host_api,
            )

    def _require_driver(self) -> AudioDriverProtocol:
        """The driver in force, which every call reaching the backend goes through.

        Raises:
            PlaybackError: If the backend was terminated and not started again.
        """
        if self._driver is None:
            raise PlaybackError("The audio backend is not initialized; call reinitialize() first")

        return self._driver

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
        return self._require_driver().supports(device_index, sample_rate)

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

        Queries the driver for the system's default output device and configures
        the manager to use it with its default sample rate. If no default device
        is found, logs a warning.
        """
        device_index = self._require_driver().default_output_index()
        if device_index is None:
            logger.warning("No default output device found")
            return

        if device_index in self._devices:
            device = self._devices[device_index]
            self._device_index = device_index
            self._sample_rate = device.default_sample_rate

    @property
    def device_index(self) -> int:
        """
        Get the currently selected audio device index.

        Returns:
            The device index.

        Raises:
            NoOutputDeviceError: If no audio device is currently selected.
        """
        if self._device_index is None:
            raise NoOutputDeviceError("No audio device selected")

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
            NoOutputDeviceError: If no audio device is currently selected.
        """
        if self._sample_rate is None:
            raise NoOutputDeviceError("No audio device selected")

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

    def get_current_device(self) -> Optional[CurrentDevice]:
        """
        Get a snapshot of the current device configuration.

        A machine offering no output device starts with nothing selected, and a refresh can take
        the selected device off the list, so both read as no current device.

        Returns:
            CurrentDevice object containing device index, name, sample rate, and host API, or
            ``None`` while no listed device is selected.
        """
        if self._device_index is None or self._sample_rate is None:
            return None

        device = self._devices.get(self._device_index)
        if device is None:
            return None

        return CurrentDevice.from_device(device, self._sample_rate)

    def require_output(self) -> CurrentDevice:
        """
        Answer the device and rate a playback opens its stream on.

        Every way to start playback asks here first, so a machine offering no output device, or a
        refresh that took the chosen one off the list, refuses the playback before any thread or
        stream starts.

        Returns:
            The device in force and the rate it plays at.

        Raises:
            NoOutputDeviceError: If no listed device is selected.
        """
        current_device = self.get_current_device()
        if current_device is None:
            logger.warning("Playback refused: no audio output device is in force")
            raise NoOutputDeviceError("No audio output device is in force")

        return current_device

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
            self.configure_device(
                device_index=device_index,
                sample_rate=current_device.sample_rate,
            )
            return

        if current_device.name:
            logger.warning(f"Audio device '{current_device.name}' not found. " f"Falling back to default device.")
        else:
            logger.info("No device specified. Initializing the default audio device.")

        self._initialize_default_device()

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
    ) -> CurrentDevice:
        """
        Configure the audio device and sample rate.

        Stops any active playback and switches to the specified device and sample rate.
        If the sample rate is not supported, falls back to the first supported rate for that device.

        A stream opened under a lease was opened on the device and rate in force at the time, so
        the new settings reach it only once it is wound down; every holder is asked to hand its
        lease back before the switch, and every claim on the output is declined while it happens.

        Args:
            device_index: Index of the device to configure.
            sample_rate: Desired sample rate in Hz.

        Returns:
            The device and the rate now in force.

        Raises:
            ValueError: If the device index is not found.
            PlaybackError: If a stream opened under a lease survives its release, which leaves the
                device and rate as they stand.
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

        with self._output_held_closed():
            self.stop()
            if not self._release_every_lease():
                raise PlaybackError("An output stream is still held; the audio device stays as it is")

            self.device_index = device_index
            self.sample_rate = sample_rate

        logger.info(f"Audio device configured: '{self.device_name}' (index={device_index}, sample_rate={sample_rate})")
        return CurrentDevice.from_device(device, sample_rate)

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

    def set_position(
        self,
        position: int,
        *,
        owner: Optional[Any],
    ) -> bool:
        """
        Seek ``owner``'s playback to a specific position in the audio.

        Ownership is checked under the lock the seek writes under, so a playback another source
        took over in the meantime stays where it is.

        Args:
            position: Target position in samples, clamped to the audio.
            owner: Identity that must match the active playback's owner for the seek to apply.

        Returns:
            bool: Whether ``owner``'s playback was moved.
        """
        with self._lock:
            if not self._playing or self._audio_data is None or self._output_owner is not owner:
                return False

            self._position = self._clamped_position(position, len(self._audio_data))
            return True

    @staticmethod
    def _clamped_position(position: int, length: int) -> int:
        return max(START_OF_AUDIO, min(position, length))

    def play_file(
        self,
        filepath: Path,
        *,
        update: bool = True,
        priority: int = 0,
    ) -> None:
        """
        Load and play an audio file.

        The output is asked for before the file is read, so a refused playback reads nothing.

        Args:
            filepath: Path to the audio file.
            update: If True, invoke position callback during playback.
            priority: Output-request priority; see :meth:`play`.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        self.require_output()
        audio = load_audio(filepath, normalize=False, quantize=False)
        self.play(audio, update=update, priority=priority)

    def play(
        self,
        audio: np.ndarray,
        *,
        update: bool = True,
        priority: int = 0,
        owner: Optional[Any] = None,
        start: int = START_OF_AUDIO,
    ) -> bool:
        """
        Play audio data.

        Starts playing the provided audio data in a background thread, after stopping
        any active playback.

        The output device exposes a single stream, so requests are ranked by ``priority``:
        this request is skipped when output is already held at a strictly higher priority
        (a buffer of this manager, or a lease). Otherwise it takes over, asking every holder of
        a lease to hand it back first.

        Args:
            audio: Audio data as numpy array (will be converted to float32).
            update: If True, invoke position callback during playback.
            priority: Output-request priority; higher wins. Callers assign the meaning.
            owner: Identity of the caller owning this playback, matched by :meth:`replace_audio`
                to swap the live buffer only while its own audio is the one playing.
            start: The sample playback begins at, clamped to the audio. It is placed before the
                playback thread starts, so the first buffer written is the one beginning there.

        Returns:
            bool: Whether this request took the output, which is what a caller following its own
                playback — drawing a cursor along it — waits for before it starts following.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        output = self.require_output()
        with self._lock:
            if self._outranked(priority):
                return False

            displaced = self._displace_claims()

        self.stop()
        self._release(displaced)

        with self._lock:
            self._audio_data = audio.astype(np.float32)
            self._position = self._clamped_position(start, len(self._audio_data))
            self._playing = True
            self._output_owner = owner
            self._active_priority = priority
            self._paused = False
            self._stop = False
            self._generation += 1
            generation = self._generation

        self._resume_event.set()
        self._playback_thread = threading.Thread(
            target=self._playback_worker,
            kwargs={
                "output": output,
                "update": update,
                "generation": generation,
            },
            daemon=True,
            name="AudioPlaybackWorker",
        )

        self._playback_thread.start()
        return True

    def replace_audio(
        self,
        audio: np.ndarray,
        *,
        owner: Optional[Any] = None,
    ) -> bool:
        """
        Swap the buffer of an in-progress playback without interrupting it.

        The playback loop reads the current buffer afresh on each chunk, so replacing it
        in place makes the change audible from the next buffer onward. Playback position is
        preserved and clamped to the new length. The swap applies only while ``owner`` matches
        the caller that started the active playback, leaving other sources untouched.

        Args:
            audio: Replacement audio data as numpy array (will be converted to float32).
            owner: Identity that must match the active playback's owner for the swap to apply.

        Returns:
            True if a live playback was replaced, False otherwise.
        """
        with self._lock:
            if not self._playing or self._audio_data is None or self._output_owner is not owner:
                return False

            self._audio_data = audio.astype(np.float32)
            self._position = min(self._position, len(self._audio_data))
            return True

    def _playback_loop(
        self,
        stream: OutputStreamProtocol,
        update: bool,
        generation: int,
    ) -> None:
        """
        Internal audio playback loop.

        Continuously reads audio chunks and writes them to the stream until stopped,
        paused, or audio ends. Respects pause state and stop flag, and ends once a newer
        playback has taken the generation over.

        Args:
            stream: The stream to write audio data to.
            update: If True, invoke position callback after each chunk.
            generation: The playback this loop plays.
        """
        while True:
            self._resume_event.wait(timeout=0.1)

            with self._lock:
                if self._stop or self._audio_data is None or generation != self._generation:
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

            write_to_stream(stream, chunk.tobytes())

            if update and self._position_callback is not None:
                self.call(self._position_callback, current_position)

    def _playback_worker(
        self,
        *,
        output: CurrentDevice,
        update: bool,
        generation: int,
    ) -> None:
        """
        Playback thread worker function.

        Opens an audio stream, runs the playback loop, and ensures cleanup. A stream the device
        refuses to open, a write it fails and a stream it fails to stop each leave the playback
        idle, as a finished one does, before the error callback reports the failure, so whoever
        follows the playback reads it stopped.

        A stop waits a while for the worker and then lets it go, so a device slow to open can bring
        the worker back once its playback was stopped, or after a newer play has begun. The worker
        acts for its own ``generation`` alone: a refusal it meets then is left unreported, a stream
        it opens then closes unplayed, and the state stands as the stop or the newer play left it.

        Args:
            output: The device and rate in force when the playback was asked for.
            update: If True, invoke position callback during playback.
            generation: The playback this worker plays, stamped by :meth:`play`.
        """
        logger.debug(f"Starting playback: device_index={output.device_index}, sample_rate={output.sample_rate}")
        try:
            self._play_generation(output=output, update=update, generation=generation)
        except PlaybackError as playback_error:
            if self._is_current(generation):
                self.call(self.on_playback_error, playback_error)

    def _play_generation(
        self,
        *,
        output: CurrentDevice,
        update: bool,
        generation: int,
    ) -> None:
        """Plays ``generation``'s audio on a stream of its own, and leaves the playback idle however that ends.

        Raises:
            PlaybackError: If the device refuses the stream, fails a write, or fails to stop the stream.
        """
        try:
            stream = self._open_stream(
                device_index=output.device_index,
                sample_rate=output.sample_rate,
                frames_per_buffer=None,
            )
            try:
                if self._is_current(generation):
                    self._playback_loop(stream, update, generation)
            finally:
                close_stream(stream)
        finally:
            self._reset_generation(generation, update=update)

    def _is_current(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation

    def _reset_generation(self, generation: int, *, update: bool) -> None:
        """Resets playback state to idle while ``generation`` is the playback in force."""
        with self._lock:
            if generation != self._generation:
                return

            self._clear_playback()

        self._report_the_start(update=update)

    def _reset(self, *, update: bool = True) -> None:
        """
        Reset playback state to idle.

        Clears playing/paused flags, resets position, and releases audio data.
        Optionally invokes position callback with position 0.

        Args:
            update: If True, invoke position callback with 0.
        """
        with self._lock:
            self._clear_playback()

        self._report_the_start(update=update)

    def _clear_playback(self) -> None:
        """Puts the playback state at idle. The caller holds the lock."""
        self._playing = False
        self._paused = False
        self._position = 0
        self._audio_data = None
        self._output_owner = None

    def _report_the_start(self, *, update: bool) -> None:
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

        Signals the playback thread to stop, waits for it to terminate (up to
        ``STOP_JOIN_SECONDS``), and resets all playback state. The stopped playback's generation
        ends here, so a worker the wait lets go of acts for no playback: a refusal it meets later
        reaches nobody, and the state stays as the stop left it. The manager keeps that worker, so
        a teardown of the backend waits for it.
        """
        with self._lock:
            self._stop = True
            self._generation += 1

        self._resume_event.set()
        if self._playback_thread is not None:
            self._let_go(self._playback_thread)

        self._playback_thread = None
        self._reset()

    def _let_go(self, worker: threading.Thread) -> None:
        """Waits a while for a stopped worker, and keeps one that outlives the wait for a teardown to join."""
        worker.join(timeout=STOP_JOIN_SECONDS)
        with self._lock:
            self._let_go_workers = [kept for kept in self._let_go_workers if kept.is_alive()]
            if worker.is_alive():
                self._let_go_workers.append(worker)

    def _join_let_go_workers(self) -> bool:
        """Waits a while for each worker a stop let go of, and reports whether every one has ended.

        Such a worker may still be opening its stream on the backend, so the backend is torn down only
        once it has ended. A worker that outlives ``LET_GO_JOIN_SECONDS`` is logged and kept, as a
        stream that outlives its release is.
        """
        with self._lock:
            workers, self._let_go_workers = self._let_go_workers, []

        outliving: List[threading.Thread] = []
        for worker in workers:
            worker.join(timeout=LET_GO_JOIN_SECONDS)
            if worker.is_alive():
                logger.error(f"AudioDeviceManager: {worker.name} outlived the teardown deadline")
                outliving.append(worker)

        with self._lock:
            self._let_go_workers.extend(outliving)

        return not outliving

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

    def is_owned_by(self, owner: Any) -> bool:
        """Whether ``owner`` holds the live output, whether it is sounding or held paused.

        Ownership tells an intentional source's own playback apart from a preview (owned by
        nobody) or another source's playback, so a source reports itself engaged only while its
        audio is the one on the device.
        """
        with self._lock:
            return self._playing and self._output_owner is owner

    def position_of(self, owner: Any) -> int:
        """Where ``owner``'s playback stands, sounding or held paused.

        The position is read under the same lock a seek writes it under, so a caller drawing a mark
        from it draws the latest seek, while a position reported earlier may already be behind it.

        Returns:
            int: The sample the playback has reached, or the start of the audio while ``owner`` holds
                no output.
        """
        with self._lock:
            if self._playing and self._output_owner is owner:
                return self._position

            return START_OF_AUDIO

    def acquire_output(
        self,
        *,
        priority: int,
        release: VoidCallback,
    ) -> Optional[OutputLease]:
        """Claim the output for a source that streams to it from a thread of its own.

        A claim is ranked the way :meth:`play` ranks a buffer: it is declined while the output is held
        strictly above ``priority``, and otherwise it takes the output over, stopping this manager's own
        playback and asking every other holder to hand its lease back. The claim is recorded under the
        lock before anything is released, so two sources asking at once are settled there and one of
        them holds the output afterwards. A holder hands its lease back before it asks for another,
        since a release winds the holder's own writing down.

        Every claim is declined while the backend is reconfigured or torn down.

        Args:
            priority: The rank of the claim; higher wins. Callers assign the meaning.
            release: Winds the caller's writing down; returns once the lease is handed back.

        Returns:
            Optional[OutputLease]: The lease to open a stream under and to hand back, or ``None`` where
                the claim is declined.

        Raises:
            NoOutputDeviceError: If no output device is in force.
        """
        self.require_output()
        lease = OutputLease(priority=priority, release=release)
        with self._lock:
            if self._output_closed or self._outranked(priority):
                return None

            displaced = self._displace_claims()
            self._claims.append(lease)

        self.stop()
        self._release(displaced)
        return lease

    def open_output_stream(
        self,
        lease: OutputLease,
        *,
        sample_rate: int,
        buffer_size: int,
    ) -> Optional[OutputStreamProtocol]:
        """Open a blocking output stream under ``lease`` for the holder to write from its own thread.

        The holder hands the lease back through :meth:`hand_back` once its writing finishes, which
        closes the stream. Until then the manager counts the stream as outstanding and calls the
        lease's release whenever it needs the backend free, so a stream is torn down by the thread
        that writes to it. A lease another claim took the output from opens nothing: the claim is
        checked before the open, and again after it, since a device can be slow to open and the
        output may change hands meanwhile.

        Args:
            lease: The claim the stream opens under.
            sample_rate: Sample rate in Hz.
            buffer_size: Frames per buffer (controls write granularity).

        Returns:
            Optional[OutputStreamProtocol]: The stream, or ``None`` where the lease no longer holds the output.

        Raises:
            PlaybackError: If the backend is not initialized, or the device refuses to open the stream.
            NoOutputDeviceError: If no output device is in force.
        """
        self._require_driver()
        output = self.require_output()
        with self._lock:
            if not self._holds(lease):
                return None

            self._outstanding.append(lease)

        try:
            stream = self._open_stream(
                device_index=output.device_index,
                sample_rate=sample_rate,
                frames_per_buffer=buffer_size,
            )
        except PlaybackError:
            self._settle(lease)
            raise

        with self._lock:
            if self._holds(lease):
                lease.stream = stream
                return stream

        try:
            close_stream(stream)
        finally:
            self._settle(lease)

        return None

    def _open_stream(
        self,
        *,
        device_index: int,
        sample_rate: int,
        frames_per_buffer: Optional[int],
    ) -> OutputStreamProtocol:
        """Opens an output stream on the device, naming a refusal the way every playback reports it.

        Both kinds of playback open their stream here, the one this manager plays and the one it hands
        out, so a reader told of a refused stream reads the same words whichever source asked.

        Raises:
            PlaybackError: If the backend is not initialized, or the device refuses to open the stream.
        """
        driver = self._require_driver()
        try:
            return driver.open_output(
                device_index=device_index,
                sample_rate=sample_rate,
                frames_per_buffer=frames_per_buffer,
            )
        except OSError as exception:
            raise PlaybackError(f"Failed to open audio stream: {exception}") from exception

    def hand_back(self, lease: OutputLease) -> None:
        """Take a lease back, closing the stream opened under it.

        Called by the holder from the thread that wrote to the stream once that writing has finished,
        and by a holder whose stream never opened. Taking the lease back is what tells the manager the
        backend is free again, so the lease is forgotten before its stream is wound down.

        Raises:
            PlaybackError: If the device fails to stop or to close the stream.
        """
        with self._lock:
            self._forget(lease)
            stream, lease.stream = lease.stream, None

        if stream is not None:
            close_stream(stream)

    def terminate(self) -> None:
        """
        Clean up and terminate the audio device manager.

        Declines every later claim on the output, stops any active playback, releases every
        lease, waits for the workers a stop let go of, and terminates the backend. A
        stream that survives its release leaves the instance running, since terminating closes
        any open stream and the owning thread would go on writing to freed memory. A worker that
        outlives the wait leaves it running too, since it may still be opening its stream. Should
        be called once you are finished with the manager.
        """
        if self._driver is None:
            return

        with self._lock:
            self._output_closed = True

        self.stop()
        if not self._release_every_lease():
            logger.error("AudioDeviceManager: an output stream is still held; the audio backend left running")
            return

        if not self._join_let_go_workers():
            logger.error("AudioDeviceManager: a playback worker is still running; the audio backend left running")
            return

        self._driver.terminate()
        self._driver = None

    @contextlib.contextmanager
    def _output_held_closed(self) -> Generator[None, None, None]:
        """Declines every claim on the output while the backend changes underneath it."""
        with self._lock:
            self._output_closed = True

        try:
            yield
        finally:
            with self._lock:
                self._output_closed = False

    def _outranked(self, priority: int) -> bool:
        """Whether the output is held strictly above ``priority``. The caller holds the lock."""
        held = [claim.priority for claim in self._claims]
        if self._playing:
            held.append(self._active_priority)

        return any(rank > priority for rank in held)

    def _holds(self, lease: OutputLease) -> bool:
        """Whether ``lease`` still claims the output. The caller holds the lock."""
        return not self._output_closed and any(claim is lease for claim in self._claims)

    def _displace_claims(self) -> List[OutputLease]:
        """Withdraws every claim, and answers the leases whose holders are to be asked to wind down.

        A withdrawn lease ranks no more and opens no stream, so a claim made afterwards is weighed against
        the holders still in force alone. A lease already opening or writing stays outstanding until its
        holder hands it back. The caller holds the lock.
        """
        displaced, self._claims = self._claims, []
        return displaced

    def _release_every_lease(self) -> bool:
        """Asks every holder to wind down; reports whether every stream was handed back."""
        with self._lock:
            leases = self._displace_claims()
            leases.extend(lease for lease in self._outstanding if not any(lease is held for held in leases))

        return self._release(leases)

    def _release(self, leases: List[OutputLease]) -> bool:
        """Asks each holder of ``leases`` to wind down; reports whether each one handed its stream back.

        A holder writes to its stream from its own thread, so only the holder can bring the writing to a
        stop. A release both stops the writer and hands the lease back through :meth:`hand_back`, which is
        what leaves the instance safe to terminate. Each release runs outside the lock, so a holder handing
        its lease back from the writing thread meets no lock the releaser holds.
        """
        for lease in leases:
            lease.release()

        with self._lock:
            outstanding = sum(1 for lease in leases if any(lease is held for held in self._outstanding))

        if outstanding:
            logger.error(f"AudioDeviceManager: {outstanding} output stream(s) outlived their release")
            return False

        return True

    def _settle(self, lease: OutputLease) -> None:
        """Counts ``lease`` off the outstanding streams once the device holds nothing of it."""
        with self._lock:
            self._outstanding = [held for held in self._outstanding if held is not lease]

    def _forget(self, lease: OutputLease) -> None:
        """Takes ``lease`` off both registries. The caller holds the lock."""
        self._claims = [claim for claim in self._claims if claim is not lease]
        self._outstanding = [held for held in self._outstanding if held is not lease]
