from threading import RLock
from typing import AbstractSet, Set


class RowExpansionMemory:
    """The rows a browser stands open, held apart by the hand that opened them.

    The reader's rows are the ones they opened themselves, and they are the shape a session writes down.
    The mode's rows are the way down the favorites mode opened on the pass the reader asked for, which
    stands for as long as the mode does. Each row is held by the tag it is addressed under, a pass
    replacing every node the model states.

    A pass writes from the tree worker while a click writes from the main thread, so one lock covers
    every answer the memory gives.
    """

    def __init__(self, reader_rows: AbstractSet[str]) -> None:
        self._lock = RLock()
        self._reader_rows: Set[str] = set(reader_rows)
        self._mode_rows: Set[str] = set()

    def __bool__(self) -> bool:
        with self._lock:
            return bool(self._reader_rows or self._mode_rows)

    @property
    def rows(self) -> Set[str]:
        """The rows the reader stands open, which is the shape a session writes down."""
        with self._lock:
            return set(self._reader_rows)

    @property
    def follows_the_mode(self) -> bool:
        """Whether the mode's way down stands open, which is what a release has rows to answer for."""
        with self._lock:
            return bool(self._mode_rows)

    def stands_open(self, node_tag: str) -> bool:
        with self._lock:
            return node_tag in self._reader_rows or node_tag in self._mode_rows

    def remember(self, node_tag: str, *, expanded: bool) -> None:
        """Holds what the reader left a row standing as, which is theirs from then on.

        A row they fold is theirs to fold whichever hand opened it, so folding it lets go of the mode's
        claim on it as well and the row stays folded.
        """
        with self._lock:
            if expanded:
                self._reader_rows.add(node_tag)
                return

            self._reader_rows.discard(node_tag)
            self._mode_rows.discard(node_tag)

    def follow(self, way_down: AbstractSet[str]) -> None:
        """Notes the way down a pass opened, which stands open for as long as the mode does."""
        with self._lock:
            self._mode_rows |= way_down

    def release(self, ways_down: AbstractSet[str]) -> None:
        """Folds the rows the mode opened, keeping the ones a row of the reader's stands on.

        A row of the mode's holding one of theirs below it holds theirs on the screen, and it therefore
        becomes the reader's to keep. What is left held the mode's opening alone, and folds with it.
        """
        with self._lock:
            self._reader_rows |= self._mode_rows & ways_down
            self._mode_rows = set()

    def hold_to(self, rows: AbstractSet[str]) -> None:
        """Holds both memories to the rows given, a row held beyond them having left the model."""
        with self._lock:
            self._reader_rows &= rows
            self._mode_rows &= rows
