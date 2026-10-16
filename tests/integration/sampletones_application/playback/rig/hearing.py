import contextlib
import threading
from typing import Callable, Dict, FrozenSet, Generic, Iterator, List, Optional

from sampletones_core.audio.output import Ending, Playback, PlaybackListener
from sampletones_core.audio.output.source import ReportT
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.types.callback import VoidCallback

from .reports import End, EndCause, Mark, OwnerLog, RowMark, Told
from .sound import Sound


class _Context(threading.local):
    """Where the thread running a notification stands: inside a gesture, a drain, both, or neither."""

    def __init__(self) -> None:
        self.gestures: int = 0
        self.delivering: bool = False


class Hearing:
    """What each owner hears, counted as the render thread takes it.

    A report counts as heard when a drain of the callback queue delivers it, which is the render thread
    taking a report the output sent. A notification an owner makes while a gesture runs answers that
    gesture, so it counts for nothing the device did. Each owner is the listener of the playbacks it
    starts, so the end report an owner takes is the one the output sent it, cause and all; a player, the
    audition and the song draw marks, and every failure told to a listener is kept, whenever and wherever
    it is told.
    """

    def __init__(
        self,
        *,
        holding: Callable[[Sound], bool],
        open_streams: Callable[[], FrozenSet[int]],
        written: Callable[[], int],
    ) -> None:
        self._holding = holding
        self._open_streams = open_streams
        self._written = written
        self._context = _Context()
        self._lock = threading.Lock()
        self._owners: Dict[int, Sound] = {}
        self._logs: Dict[Sound, OwnerLog] = {sound: OwnerLog() for sound in Sound}
        self._rows: List[RowMark] = []
        self._told: List[Told] = []
        self._end_handlers: Dict[Sound, List[VoidCallback]] = {sound: [] for sound in Sound}

    @contextlib.contextmanager
    def gesture(self) -> Iterator[None]:
        """Marks the block as a gesture the reader made, whose own notifications report nothing heard."""
        self._context.gestures += 1
        try:
            yield
        finally:
            self._context.gestures -= 1

    @contextlib.contextmanager
    def delivering(self) -> Iterator[None]:
        """Marks the block as a drain, which delivers what the output reported."""
        delivering, self._context.delivering = self._context.delivering, True
        try:
            yield
        finally:
            self._context.delivering = delivering

    @property
    def heard(self) -> bool:
        return self._context.delivering and self._context.gestures == 0

    def owns(self, sound: Sound, owner: PlaybackListener[ReportT]) -> None:
        """Names the sound whose playbacks ``owner`` starts and listens to."""
        self._owners[id(owner)] = sound

    def listening(self, owner: PlaybackListener[ReportT]) -> PlaybackListener[ReportT]:
        """The listener a playback of ``owner`` reports to: the owner, with the rig hearing its end beside it."""
        return _HeardListener(owner, sound=self._owners[id(owner)], hearing=self)

    def log(self, sound: Sound) -> OwnerLog:
        with self._lock:
            log = self._logs[sound]
            return OwnerLog(marks=list(log.marks), ends=list(log.ends))

    @property
    def rows(self) -> List[RowMark]:
        with self._lock:
            return list(self._rows)

    @property
    def told(self) -> List[Told]:
        with self._lock:
            return list(self._told)

    def on_end(self, sound: Sound, action: VoidCallback) -> None:
        """Runs ``action`` on the render thread each time ``sound``'s owner hears an end."""
        self._end_handlers[sound].append(action)

    def marked(self, sound: Sound, position: int) -> None:
        if self.heard:
            with self._lock:
                log = self._logs[sound]
                log.marks.append(Mark(position=position, written=self._written(), ends_heard=len(log.ends)))

    def rowed(self, order_position: int, row_index: int) -> None:
        if self.heard:
            position = SongPosition(order_position=order_position, row_index=row_index)
            with self._lock:
                self._rows.append(RowMark(position=position, written=self._written()))

    def tell(self, listener: Optional[Sound], error: Exception) -> None:
        with self._lock:
            self._told.append(Told(listener=listener, error=error))

    def ended(self, sound: Sound, ending: Ending) -> None:
        if not self.heard:
            return

        end = End(cause=EndCause(ending.cause.value), holding=self._holding(sound), open_streams=self._open_streams())
        with self._lock:
            self._logs[sound].ends.append(end)

        for action in list(self._end_handlers[sound]):
            action()


class _HeardListener(Generic[ReportT]):
    """An owner's listener with the rig hearing each end report once the owner has taken it."""

    def __init__(self, owner: PlaybackListener[ReportT], *, sound: Sound, hearing: Hearing) -> None:
        self._owner = owner
        self._sound = sound
        self._hearing = hearing

    def positioned(self, playback: Playback[ReportT], report: ReportT) -> None:
        self._owner.positioned(playback, report)

    def ended(self, playback: Playback[ReportT], ending: Ending) -> None:
        self._owner.ended(playback, ending)
        self._hearing.ended(self._sound, ending)
