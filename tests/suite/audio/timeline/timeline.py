import threading
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set, Type

import numpy as np

from .events import Closed, EventT, Opened, TimelineEvent, Violation, Written
from .violations import ViolationKind


@dataclass
class Timeline:
    """Everything the fake device was asked to do, in the order it was asked, from whichever thread asked.

    The timeline is the witness a playback case reads: which streams opened and closed, what each one
    played, and every use of the device a correct playback never makes.
    """

    _events: List[TimelineEvent] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, event: TimelineEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> List[TimelineEvent]:
        with self._lock:
            return list(self._events)

    def count(self) -> int:
        """How many events the timeline holds, which marks a moment to compare a later event's index with."""
        with self._lock:
            return len(self._events)

    def of(self, kind: Type[EventT]) -> List[EventT]:
        """The events of one kind, in the order they happened."""
        return [event for event in self.events() if isinstance(event, kind)]

    def violations(self) -> List[ViolationKind]:
        return [event.kind for event in self.of(Violation)]

    def written(self, stream: Optional[int] = None) -> np.ndarray:
        """Every sample the device received, on one stream or on all of them, in the order it arrived."""
        blocks = [event.samples for event in self.of(Written) if stream is None or event.stream == stream]
        return np.concatenate(blocks) if blocks else np.zeros(0, dtype=np.float32)

    def sounding_samples(self) -> int:
        """How many samples the device received that carry sound."""
        return int(np.count_nonzero(self.written()))

    def open_streams(self) -> Set[int]:
        """The streams opened and not closed yet."""
        opened = {event.stream for event in self.of(Opened)}
        return opened - {event.stream for event in self.of(Closed)}

    def most_streams_open(self) -> int:
        """The most streams the device held open at one moment."""
        most = 0
        open_now: Set[int] = set()
        for event in self.events():
            if isinstance(event, Opened):
                open_now.add(event.stream)
                most = max(most, len(open_now))
            elif isinstance(event, Closed):
                open_now.discard(event.stream)

        return most

    def streams(self) -> Sequence[int]:
        """The streams in the order they opened."""
        return [event.stream for event in self.of(Opened)]
