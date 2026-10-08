from typing import List, Protocol


class Hold(Protocol):
    """Work a scenario keeps under way until it lets go, so a gesture lands while the work runs."""

    def release(self) -> None:
        """Lets the work carry on to its end."""


class Holds:
    """Every hold a scenario put on the application's work, let go together before the scenario leaves.

    Leaving waits for work in flight, so the holds are released before the exit is asked for.
    """

    def __init__(self) -> None:
        self._holds: List[Hold] = []

    def add(self, hold: Hold) -> None:
        """Puts ``hold`` among the holds released together."""
        self._holds.append(hold)

    def release_all(self) -> None:
        """Releases every hold that was added."""
        for hold in self._holds:
            hold.release()
