import contextlib
import threading
from typing import Callable, Dict, FrozenSet, Iterator, List, Optional

from sampletones_application.services.song_player.result import (
    SongPlaybackError,
    SongPlaybackStopped,
    SongPlayerResult,
    SongPositionUpdate,
)
from sampletones_core.constants.audio import START_OF_AUDIO
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
    taking a report the device sent. A notification an owner makes while a gesture runs answers that
    gesture, so it counts for nothing the device did. Today's owners take their reports in these shapes:

    - a reconstruction or instruction player hears its end as a transport notification a drain delivers,
      and draws every mark it is handed;
    - the song hears its end as the service's terminal result, and draws its rows;
    - the audition draws every position it is handed, and hears its end as the final zero;
    - a voice or a file preview has its failures alone to hear.

    Every failure told to a listener is kept, whenever and wherever it is told.
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
        """Marks the block as a drain, which delivers what the device reported."""
        delivering, self._context.delivering = self._context.delivering, True
        try:
            yield
        finally:
            self._context.delivering = delivering

    @property
    def heard(self) -> bool:
        return self._context.delivering and self._context.gestures == 0

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

    def notified(self, sound: Sound) -> None:
        if self.heard:
            self._end(sound, None)

    def auditioned(self, position: int) -> None:
        if not self.heard:
            return

        if position == START_OF_AUDIO:
            self._end(Sound.AUDITION, None)
            return

        self.marked(Sound.AUDITION, position)

    def rowed(self, order_position: int, row_index: int) -> None:
        if self.heard:
            position = SongPosition(order_position=order_position, row_index=row_index)
            with self._lock:
                self._rows.append(RowMark(position=position, written=self._written()))

    def song_result(self, result: SongPlayerResult) -> None:
        match result:
            case SongPositionUpdate():
                return
            case SongPlaybackStopped():
                self._end(Sound.SONG, None)
            case SongPlaybackError():
                self._end(Sound.SONG, EndCause.FAILED)

    def tell(self, listener: Optional[Sound], error: Exception) -> None:
        with self._lock:
            self._told.append(Told(listener=listener, error=error))

    def _end(self, sound: Sound, cause: Optional[EndCause]) -> None:
        end = End(cause=cause, holding=self._holding(sound), open_streams=self._open_streams())
        with self._lock:
            self._logs[sound].ends.append(end)

        for action in list(self._end_handlers[sound]):
            action()
