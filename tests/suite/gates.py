from typing import List

import pytest

from sampletones_shared.types.callback import VoidCallback


class HeldGate:
    """A gate a case opens by hand, the way the open reconstruction's edits hold a gesture until they land."""

    def __init__(self) -> None:
        self.holding = False
        self._held: List[VoidCallback] = []

    def __call__(self, proceed: VoidCallback) -> None:
        if self.holding:
            self._held.append(proceed)
            return

        proceed()

    @property
    def held(self) -> int:
        """How many gestures wait at the gate."""
        return len(self._held)

    def release(self) -> None:
        """Opens the gate, which runs every gesture waiting at it in the order it arrived."""
        self.holding = False
        held, self._held = self._held, []
        for proceed in held:
            proceed()


@pytest.fixture
def held_gate() -> HeldGate:
    """A gate holding every gesture that reaches it until the case releases it."""
    gate = HeldGate()
    gate.holding = True
    return gate
