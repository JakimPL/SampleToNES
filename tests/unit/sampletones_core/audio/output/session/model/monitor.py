from collections.abc import Hashable
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sampletones_core.audio.output.ending import EndCause, Ending


@dataclass(frozen=True)
class Demand:
    """What the playbacks present ask of the stream, by the contract: to hold the output, to sound, and to play a
    finished tail out."""

    wanted: bool
    mixing: bool
    tail: bool


@dataclass
class Expectation:
    """What the contract says about one playback, kept apart from the core's own state.

    Attributes:
        rank: The rank the playback claimed the output at.
        first: The first ending offered while it held the output, which decides its end.
        upgrade: A failure offered after it finished and before its report, which its report names instead.
        paused: Whether its owner holds it paused.
        commanded: Whether a command waits for its next read.
        reported: Whether its end report went out.
    """

    rank: int
    first: Optional[Ending]
    upgrade: Optional[Ending]
    paused: bool
    commanded: bool
    reported: bool

    @property
    def engaged(self) -> bool:
        return self.first is None

    @property
    def ending(self) -> Optional[Ending]:
        """The ending the playback's report has to name, once its end is decided."""
        return self.upgrade if self.upgrade is not None else self.first

    @property
    def tail(self) -> bool:
        """Whether the playback finished and waits for its report, its tail still to play out."""
        ending = self.ending
        return not self.reported and ending is not None and ending.cause is EndCause.FINISHED


class Monitor:
    """A reference for the session core: what every playback was offered, and so what its report has to say.

    The first cause offered while a playback holds the output decides its end, and a failure offered while a
    finished playback waits for its tail replaces the finish. The monitor learns causes from the events the
    case sends, which is what lets it judge the core's reports without reading the core's own decisions.
    """

    def __init__(self) -> None:
        self._expectations: Dict[int, Expectation] = {}
        self.closing: bool = False

    def claimed(self, key: int, *, rank: int) -> None:
        self._expectations[key] = Expectation(
            rank=rank,
            first=None,
            upgrade=None,
            paused=False,
            commanded=False,
            reported=False,
        )

    def expectation(self, key: int) -> Expectation:
        return self._expectations[key]

    def keys(self) -> Tuple[int, ...]:
        return tuple(self._expectations)

    def engaged(self) -> List[int]:
        return [key for key, expectation in self._expectations.items() if expectation.engaged]

    def unreported(self) -> List[int]:
        return [key for key, expectation in self._expectations.items() if not expectation.reported]

    def outranked(self, rank: int) -> bool:
        return any(self._expectations[key].rank > rank for key in self.engaged())

    def offer(self, key: int, ending: Ending) -> None:
        """Offers ``key`` an end, which decides it while it holds the output, or cuts a finished tail short."""
        expectation = self._expectations[key]
        if expectation.reported:
            return

        if expectation.first is None:
            expectation.first = ending
            expectation.paused = False
        elif expectation.tail and ending.cause is EndCause.FAILED and expectation.upgrade is None:
            expectation.upgrade = ending

    def offer_engaged(self, ending: Ending) -> None:
        for key in self.engaged():
            self.offer(key, ending)

    def cut_tails(self, ending: Ending) -> None:
        for key, expectation in self._expectations.items():
            if expectation.tail:
                self.offer(key, ending)

    def reported(self, key: int) -> None:
        self._expectations[key].reported = True

    def key(self) -> Hashable:
        """Equal for two monitors expecting the same of every playback still present, in claim order."""
        live = tuple(
            (value.rank, value.first, value.upgrade, value.paused, value.commanded)
            for value in self._expectations.values()
            if not value.reported
        )
        return (live, self.closing)
