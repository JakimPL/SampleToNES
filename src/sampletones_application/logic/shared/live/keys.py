import threading
from functools import partial
from typing import Callable, Optional, Tuple

from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_core.audio.output import Ending, Playback, Post
from sampletones_core.audio.output.source import FailureReport
from sampletones_shared.exceptions import PlaybackError

from .key import LiveKey
from .position import LiveReport
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

    Where a note stands reaches the follower of the press that struck it, on the render thread, so whoever
    struck it draws it. A note giving way to another press, ending, or ending with its playback is told to
    its follower as ``None``, once.
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
        self._playback: Optional[Playback[LiveReport]] = None
        self._source: Optional[LiveNoteSource] = None
        self._sustained: bool = False
        self._followed: Optional[Tuple[Playback[LiveReport], Strike]] = None

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

    def positioned(self, playback: Playback[LiveReport], report: LiveReport) -> None:
        """Hands where the note sounding stands to the follower of its press, telling the one before it went."""
        with self._lock:
            if playback is not self._playback:
                return

        strike = None if report is None else report.strike
        if self._followed is not None and self._followed[1] is not strike:
            self._unfollow()

        if report is None:
            return

        self._followed = (playback, report.strike)
        if report.strike.follower is not None:
            report.strike.follower(report.position)

    def ended(self, playback: Playback[LiveReport], ending: Ending) -> None:
        """Lets the playback go, telling its note's follower and the failure where it failed."""
        if self._followed is not None and self._followed[0] is playback:
            self._unfollow()

        with self._lock:
            if playback is not self._playback:
                return

            self._playback, self._source = None, None

        if ending.error is not None:
            self._failed(ending.error)

    def _unfollow(self) -> None:
        """Tells the follower of the note followed that it sounds no more."""
        if self._followed is None:
            return

        _playback, strike = self._followed
        self._followed = None
        if strike.follower is not None:
            strike.follower(None)

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
