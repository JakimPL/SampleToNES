import threading
from typing import Callable, List, Mapping, Optional, Tuple

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE
from sampletones_shared.exceptions import NoOutputDeviceError
from sampletones_shared.types.callback import VoidCallback

from .lifecycle import StreamAction
from .playback import PlaybackFeed
from .session import EndReport, SessionCore, SourceRead, Step
from .settings import OutputSettings

RefreshListener = Callable[[DeviceCatalog], None]


class OutputArbiter:
    """The output's decisions under one lock, shared by the render thread and the thread writing to the device.

    It holds the session core, the settings the next stream opens with, the refreshes asked for, and whether
    a writer runs. A request that leaves the writer something to do starts one where none runs, and wakes a
    writer asleep beside a paused sound. Each call is decided at once, so the render thread waits on no device.

    An end decided by a request from the render thread closes the playback's source at once, outside the
    lock, which wakes a read waiting for its sound.
    """

    def __init__(self, *, start_writer: VoidCallback) -> None:
        """Holds what starts a writer.

        Args:
            start_writer: Starts the thread writing to the device, called under the lock.
        """
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._core: SessionCore[PlaybackFeed] = SessionCore()
        self._settings = OutputSettings(device=None, buffer_size=DEFAULT_BUFFER_SIZE)
        self._refreshes: List[RefreshListener] = []
        self._writing: bool = False
        self._start_writer = start_writer

    @property
    def is_sounding(self) -> bool:
        """Whether any playback holds the output, from its claim until its end is decided."""
        with self._lock:
            return self._core.is_sounding

    @property
    def settings(self) -> OutputSettings:
        with self._lock:
            return self._settings

    def claim(self, feed: PlaybackFeed, *, rank: int) -> bool:
        """Asks for the output for a new playback; answers whether the playback holds it.

        Raises:
            NoOutputDeviceError: If no device is in force.
        """
        with self._lock:
            if self._settings.device is None:
                raise NoOutputDeviceError("No audio output device is in force")

            if not self._core.claim(feed, rank=rank):
                return False

            self._prompt_writer()

        self._close_ending()
        return True

    def stop_all(self) -> None:
        with self._lock:
            self._core.stop_all()
            self._wake.notify_all()

        self._close_ending()

    def configure(self, settings: OutputSettings) -> None:
        """Takes the settings the next stream opens with; a device or rate changed ends every playback present."""
        with self._lock:
            changed = settings.device != self._settings.device
            self._settings = settings
            if changed and self._core.reconfigure():
                self._prompt_writer()

        self._close_ending()

    def refresh(self, listener: RefreshListener) -> bool:
        """Asks for the backend to be renewed, which ends every playback present and tells ``listener`` the devices.

        Returns:
            bool: Whether the output takes the request, which a closing output refuses.
        """
        with self._lock:
            if not self._core.reconfigure():
                return False

            self._refreshes.append(listener)
            self._prompt_writer()

        self._close_ending()
        return True

    def close(self) -> None:
        """Closes the output for good: every playback present ends, and every later claim is declined."""
        with self._lock:
            self._core.close()
            self._wake.notify_all()

        self._close_ending()

    def abandon(self) -> Tuple[EndReport[PlaybackFeed], ...]:
        """Ends every playback present at once, for a teardown that stopped waiting for the writer."""
        with self._lock:
            return self._core.abandon()

    def is_engaged(self, feed: PlaybackFeed) -> bool:
        with self._lock:
            return self._core.is_engaged(feed)

    def is_paused(self, feed: PlaybackFeed) -> bool:
        with self._lock:
            return self._core.is_paused(feed)

    def pause(self, feed: PlaybackFeed) -> bool:
        with self._lock:
            return self._core.pause(feed)

    def resume(self, feed: PlaybackFeed) -> bool:
        with self._lock:
            resumed = self._core.resume(feed)
            self._wake.notify_all()
            return resumed

    def stop(self, feed: PlaybackFeed) -> bool:
        with self._lock:
            stopped = self._core.stop(feed)
            self._wake.notify_all()

        if stopped:
            feed.close()

        return stopped

    def command(self, feed: PlaybackFeed, action: VoidCallback) -> bool:
        with self._lock:
            if not self._core.command(feed):
                return False

            feed.enqueue(action)
            return True

    def fail(self, feed: PlaybackFeed, error: Exception) -> bool:
        """Ends a playback whose source failed between reads, which wakes a writer asleep beside it paused."""
        with self._lock:
            failed = self._core.fail(feed, error)
            self._wake.notify_all()

        if failed:
            feed.close()

        return failed

    def next_step(self) -> Step[PlaybackFeed]:
        """Answers what the writer does next, sleeping while every playback present stands paused.

        A step with nothing to report and nothing to do waits for the next request under the lock that decided
        it, so a request made meanwhile always reaches it. A write takes the commands of each playback it mixes,
        and an exit lets the writer go, so the next request starts another.
        """
        with self._lock:
            while True:
                step = self._core.next_step()
                if step.action is not StreamAction.WAIT or step.reports:
                    break

                self._wake.wait()

            match step.action:
                case StreamAction.WRITE:
                    for feed in step.mixed:
                        feed.take_commands()
                case StreamAction.EXIT:
                    self._writing = False

            return step

    def opened(self) -> None:
        with self._lock:
            self._core.opened()

    def open_failed(self, error: Exception) -> None:
        with self._lock:
            self._core.open_failed(error)

    def wrote(self, reads: Mapping[PlaybackFeed, SourceRead]) -> Tuple[PlaybackFeed, ...]:
        with self._lock:
            return self._core.wrote(reads)

    def write_failed(self, error: Exception, reads: Mapping[PlaybackFeed, SourceRead]) -> None:
        with self._lock:
            self._core.write_failed(error, reads)

    def closed(self, error: Optional[Exception]) -> None:
        with self._lock:
            self._core.closed(error)

    def renewing(self) -> bool:
        """Whether a refresh waits for the backend to be renewed."""
        with self._lock:
            return bool(self._refreshes)

    def reconfigured(self, catalog: Optional[DeviceCatalog]) -> List[RefreshListener]:
        """The settings are taken, with the device in force found again in a renewed backend's ``catalog``.

        A refresh asked for after the writer looked for one waits for the renewal that follows.

        Returns:
            List[RefreshListener]: The refreshes the renewal answers, to be told ``catalog``.
        """
        with self._lock:
            refreshes: List[RefreshListener] = []
            if catalog is not None:
                device = self._settings.device
                located = None if device is None else catalog.locate(device)
                self._settings = OutputSettings(device=located, buffer_size=self._settings.buffer_size)
                refreshes, self._refreshes = self._refreshes, []

            if not self._refreshes:
                self._core.reconfigured()

            return refreshes

    def _prompt_writer(self) -> None:
        """Starts a writer where none runs, and wakes one asleep. The caller holds the lock."""
        if not self._writing:
            self._start_writer()
            self._writing = True

        self._wake.notify_all()

    def _close_ending(self) -> None:
        """Closes the source of every playback whose end is decided, which wakes a read waiting for its sound."""
        with self._lock:
            ending = self._core.ending()

        for feed in ending:
            feed.close()
