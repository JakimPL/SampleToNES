import threading
from functools import partial
from typing import Callable, Optional

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio.output import Ending, Playback, Post
from sampletones_core.audio.output.source import FailureReport
from sampletones_shared.exceptions import PlaybackError

from .key import LiveKey
from .source import LiveNoteSource
from .strike import Strike

SourceCommand = Callable[[LiveNoteSource], None]


class LiveKeysLogic:
    """The one owner of the keys played live, from either keyboard, and of the playback they sound through.

    A press claims the output as a preview where no live playback holds it, and reaches the playback holding
    it otherwise, so keys played one after another sound on one playback and one stream. A release and the
    pedal reach the playback holding the output alone, so a key lifted after a stop or a takeover changes
    nothing heard. The pedal's state belongs to the pedal, so it outlives a playback, and a press after the
    pedal went down meets it held.

    A key reaches the sound from the thread it was played on: the render thread for a computer key, the MIDI
    thread for a MIDI one. Each call is decided under one lock and posts to the playback, which runs it on
    the writer's thread. A claim refused for want of a device is posted to ``failed`` on the render thread,
    and a playback ending in failure is told there as well.
    """

    def __init__(
        self,
        previews: PreviewPlayer,
        *,
        post: Post,
        failed: FailureReport,
        linger_seconds: float,
    ) -> None:
        """Holds what the keys sound through and who hears of a failure.

        Args:
            previews: The preview player the keys' playback claims the output through, so Stop reaches it.
            post: Carries a failure to the render thread.
            failed: Tells the reader what kept a key silent, on the render thread.
            linger_seconds: The silence a playback plays once nothing holds it, before it ends.
        """
        self._previews = previews
        self._post = post
        self._failed = failed
        self._linger_seconds = linger_seconds
        self._lock = threading.Lock()
        self._playback: Optional[Playback[None]] = None
        self._source: Optional[LiveNoteSource] = None
        self._sustained: bool = False

    def key_down(self, strike: Strike) -> None:
        """Presses a key, on the playback holding the output or on a new one claiming it."""
        with self._lock:
            if not self._commanded(lambda source: source.press(strike)):
                self._start(strike)

    def key_up(self, key: LiveKey) -> None:
        """Lifts a key on the playback holding the output."""
        with self._lock:
            self._commanded(lambda source: source.release(key))

    def pedal(self, down: bool) -> None:
        """Takes the sustain pedal's state, for the playback holding the output and every one after it."""
        with self._lock:
            self._sustained = down
            self._commanded(lambda source: source.pedal(down))

    def silence(self) -> None:
        """Ends every key's note at once, as a keyboard's "all notes off" asks; the pedal keeps its state."""
        with self._lock:
            playback, self._playback, self._source = self._playback, None, None

        if playback is not None:
            playback.stop()

    def positioned(self, _playback: Playback[None], _report: None) -> None:
        """Hears where a live playback stands, which carries no mark to draw."""
        return None

    def ended(self, playback: Playback[None], ending: Ending) -> None:
        """Lets the playback go, telling the failure where it failed."""
        with self._lock:
            if playback is not self._playback:
                return

            self._playback, self._source = None, None

        if ending.error is not None:
            self._failed(ending.error)

    def _commanded(self, command: SourceCommand) -> bool:
        """Runs ``command`` on the source of the playback held; answers whether that playback still plays."""
        if self._playback is None or self._source is None:
            return False

        return self._playback.command(partial(command, self._source))

    def _start(self, strike: Strike) -> None:
        """Claims the output for a playback whose first key is ``strike``, pressed before any thread reads it."""
        source = LiveNoteSource(sustained=self._sustained, linger_seconds=self._linger_seconds)
        source.press(strike)
        try:
            playback = self._previews.play_source(source, rank=PlaybackPriority.PREVIEW, listener=self)
        except PlaybackError as error:
            self._post(partial(self._failed, error))
            return

        if playback is not None:
            self._playback, self._source = playback, source
