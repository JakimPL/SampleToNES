from collections import deque
from collections.abc import Hashable
from dataclasses import dataclass
from typing import Callable, Deque, Final, Sequence, Set, Tuple

from .events import Event
from .runner import SessionRun

MOST_STATES: Final[int] = 200_000

Word = Tuple[Event, ...]


@dataclass(frozen=True)
class Exploration:
    """How far a model check reached: the states it met, and the deepest word it needed to meet them."""

    states: int
    deepest: int


def explore(
    alphabet: Sequence[Event],
    *,
    most_claims: int,
    check: Callable[[SessionRun, Word], None],
) -> Exploration:
    """Meets every state a session core reaches from its start over ``alphabet``, each one once.

    The states are met breadth first, so the word reaching each is one of the shortest. Every event is applied
    from every state met, and ``check`` runs on every state the first time it is met. Two runs with equal keys
    answer every later event alike, so meeting each state once covers every word, of any length.

    Raises:
        AssertionError: Naming the shortest word that broke a rule, or the bound when the states run past it.
    """
    root = SessionRun(most_claims=most_claims)
    seen: Set[Hashable] = {root.key()}
    frontier: Deque[Tuple[SessionRun, Word]] = deque([(root, ())])
    deepest = 0
    while frontier:
        run, word = frontier.popleft()
        for event in alphabet:
            if not run.moves(event):
                continue

            child = run.copy()
            reached = (*word, event)
            try:
                child.apply(event)
            except AssertionError as error:
                raise AssertionError(f"{_spelled(reached)}: {error}") from error

            key = child.key()
            if key in seen:
                continue

            seen.add(key)
            assert len(seen) <= MOST_STATES, f"the states ran past {MOST_STATES}"
            try:
                check(child, reached)
            except AssertionError as error:
                raise AssertionError(f"{_spelled(reached)}: {error}") from error

            deepest = max(deepest, len(reached))
            frontier.append((child, reached))

    return Exploration(states=len(seen), deepest=deepest)


def _spelled(word: Word) -> str:
    return " ".join(event.value for event in word) or "(the empty word)"
