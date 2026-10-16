import threading
from typing import Final, List, Optional

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.driver import AudioDriverFactory
from sampletones_shared.logger import logger

from .arbiter import OutputArbiter, RefreshListener
from .backend import AudioBackend
from .playback import Playback, PlaybackListener, Post
from .settings import OutputSettings
from .source import AudioSource, ReportT
from .threads import AudioThreads
from .writer import StreamSession

WRITER_NAME: Final[str] = "AudioOutputWriter"


class AudioOutput:
    """The one output device every sound in the application plays through, and the one stream it holds.

    An owner plays a source at a rank and gets back the playback it holds, or ``None`` where a sound ranked
    above it holds the output. A claim ranked below the holder is declined, and any other takes the output
    from every playback holding it. One thread writes to the device, started by the request that gives it
    something to do and ended once nothing is left, so the render thread waits on no device: a stop, a
    device change and a refresh are each decided at once and carried out by that thread.

    The output holds the backend from its construction until the teardown. ``close`` waits for every audio
    thread up to a deadline, reports each one that outlives it, and terminates the backend unless a writer
    is among them, since that writer may still be inside a call to the device.
    """

    def __init__(self, driver_factory: AudioDriverFactory, *, post: Post) -> None:
        """Starts the backend and lists its devices.

        Args:
            driver_factory: Creates each instance of the backend the output plays on.
            post: Carries a playback's reports to its owner's thread, in the order they are made.
        """
        self._post = post
        self._backend = AudioBackend(driver_factory)
        self._catalog = DeviceCatalog.read(self._backend.driver)
        self._threads = AudioThreads()
        self._writers: List[threading.Thread] = []
        self._arbiter = OutputArbiter(start_writer=self._start_writer)

    @property
    def catalog(self) -> DeviceCatalog:
        """The devices the backend listed as the output started."""
        return self._catalog

    @property
    def threads(self) -> AudioThreads:
        """The registry a source starts a thread of its own through, so the teardown waits for it."""
        return self._threads

    @property
    def is_sounding(self) -> bool:
        """Whether any sound holds the output, from its claim until its end is decided."""
        return self._arbiter.is_sounding

    def play(
        self,
        source: AudioSource[ReportT],
        *,
        rank: int,
        listener: PlaybackListener[ReportT],
    ) -> Optional[Playback[ReportT]]:
        """Claims the output for ``source`` at ``rank``.

        Args:
            source: What the sound is read from.
            rank: The claim's rank; a claim ranked below the holder is declined.
            listener: The owner, which hears the playback's positions and its end report.

        Returns:
            Optional[Playback[ReportT]]: The playback the owner holds, or ``None`` where the claim is declined.

        Raises:
            NoOutputDeviceError: If no device is in force.
        """
        playback = Playback(
            source,
            listener=listener,
            post=self._post,
            control=self._arbiter,
        )
        if not self._arbiter.claim(playback, rank=rank):
            return None

        return playback

    def stop_all(self) -> None:
        """Ends every sound at once."""
        self._arbiter.stop_all()

    def configure(self, settings: OutputSettings) -> None:
        """Takes the settings the next stream opens with.

        A change of device or rate ends every sound playing, and the next sound opens on the new device. A new
        buffer size waits for the next stream, so a sound playing carries on.
        """
        self._arbiter.configure(settings)

    def refresh(self, listener: RefreshListener) -> None:
        """Renews the backend so it lists the devices as they stand now, and tells ``listener`` what it lists.

        Every sound playing ends, and the device in force is found again by its name.
        """
        self._arbiter.refresh(listener)

    def close(self, *, deadline_seconds: float) -> None:
        """Ends every sound for good and waits up to ``deadline_seconds`` for every audio thread to end.

        Each thread outliving the deadline is reported. The backend is terminated once every writer has
        ended, and is left running while one still might reach the device, whose playbacks are then ended
        from here.
        """
        self._arbiter.close()
        survivors = self._threads.join(deadline_seconds=deadline_seconds)
        for thread in survivors:
            logger.error(f"AudioOutput: {thread.name} outlived the teardown deadline")

        if any(writer in survivors for writer in self._writers):
            for report in self._arbiter.abandon():
                report.key.end(report.ending)
                report.key.close()

            logger.error("AudioOutput: a writer still reaches the device; the audio backend left running")
            return

        self._backend.terminate()

    def _start_writer(self) -> None:
        session = StreamSession(self._arbiter, self._backend, post=self._post)
        writer = self._threads.start(session.run, name=WRITER_NAME)
        self._writers = [kept for kept in self._writers if kept.is_alive()]
        self._writers.append(writer)
