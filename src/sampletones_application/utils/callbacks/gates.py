from functools import partial
from typing import Callable, Generic, ParamSpec, Sequence, Tuple, TypeVar

from sampletones_shared.types.callback import VoidCallback

Wait = Callable[[VoidCallback], None]
Gate = Callable[[VoidCallback, VoidCallback], None]

GestureParameters = ParamSpec("GestureParameters")
GestureResult = TypeVar("GestureResult")


def ignore() -> None:
    """Answers a request turned away that nothing waits on, so the request ends where it stopped."""


def waiting(wait: Wait) -> Gate:
    """``wait`` as a gate that holds a request until it may go on, and then lets it through.

    Args:
        wait: What a request waits on, such as the edits of the open reconstruction.
    """

    def gate(proceed: VoidCallback, _decline: VoidCallback) -> None:
        wait(proceed)

    return gate


def pass_gates(
    gates: Sequence[Gate],
    arrive: VoidCallback,
    decline: VoidCallback,
) -> None:
    """Runs each gate in turn, and calls ``arrive`` once the last one lets the request through.

    Each gate receives a callback that runs the gates after it, and ``decline``. A gate checks what it
    guards when it is reached: it calls the first at once, or asks a question whose answer calls one of
    the two. An earlier question is therefore answered before a later gate checks, and a state that
    cleared meanwhile asks nothing. A request ends in ``arrive`` or in ``decline``, so whoever waits on
    it hears how it ended.

    Args:
        gates: What stands between a request and ``arrive``, in the order the gates are asked.
        arrive: What runs once every gate has let the request through.
        decline: What runs once a gate turns the request away.
    """
    if not gates:
        arrive()
        return

    gates[0](partial(pass_gates, gates[1:], arrive, decline), decline)


def gated(
    wait: Wait,
    gesture: Callable[GestureParameters, GestureResult],
) -> Callable[GestureParameters, None]:
    """``gesture`` as a callback that waits on ``wait`` before it runs, with the arguments it was called with.

    A menu item, a shortcut or a panel hook takes the callback in the gesture's place, so whatever
    reaches the gesture waits first. The callback discards what the gesture returns.

    Args:
        wait: What the gesture waits on.
        gesture: What runs once the wait lets it through.
    """

    def call(*args: GestureParameters.args, **kwargs: GestureParameters.kwargs) -> None:
        def run() -> None:
            gesture(*args, **kwargs)

        wait(run)

    return call


class SingleFlight(Generic[GestureParameters]):
    """A gesture that holds one conversation at a time, absorbing a repeat asked for while one is in flight.

    The conversation is the gates the gesture passes. It is in flight from the moment the gesture is
    asked for until the gates let it through or turn it away. A gesture asked for twice before its
    question is answered therefore asks once, and one asked for after the answer asks again. A gate
    that raises ends the flight too, so one failure leaves the gesture to be asked for again.
    """

    def __init__(
        self,
        gates: Sequence[Gate],
        arrive: Callable[GestureParameters, GestureResult],
    ) -> None:
        self._gates: Tuple[Gate, ...] = tuple(gates)
        self._arrive = arrive
        self._in_flight: bool = False

    @property
    def in_flight(self) -> bool:
        """Whether a conversation of this gesture has been asked for and has not yet ended."""
        return self._in_flight

    def __call__(self, *args: GestureParameters.args, **kwargs: GestureParameters.kwargs) -> None:
        if self._in_flight:
            return

        def arrive() -> None:
            self._land()
            self._arrive(*args, **kwargs)

        self._in_flight = True
        asked = False
        try:
            pass_gates(self._gates, arrive, self._land)
            asked = True
        finally:
            if not asked:
                self._land()

    def _land(self) -> None:
        self._in_flight = False
