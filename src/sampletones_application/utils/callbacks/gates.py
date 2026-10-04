from abc import ABC, abstractmethod
from functools import partial
from typing import Callable, Generic, Optional, ParamSpec, Sequence, TypeVar

from sampletones_shared.types.callback import VoidCallback

Wait = Callable[[VoidCallback], None]
Gate = Callable[[VoidCallback, VoidCallback], None]

GestureParameters = ParamSpec("GestureParameters")
GestureResult = TypeVar("GestureResult")


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


class SingleFlight(ABC, Generic[GestureParameters]):
    """A gesture that holds one conversation at a time, and lets one request through at its end.

    The conversation is the gates the gesture passes. It is in flight from the moment the gesture is
    asked for until the gates let it through or turn it away, and a gesture asked for after that asks
    again. A gesture asked for while it is in flight asks nothing, and the kind of flight decides which
    request its end lets through. A conversation that turns the gesture away drops the request it
    holds. A gate that raises ends the flight the same way, so one failure leaves the gesture to be
    asked for again.
    """

    def __init__(self, arrive: Callable[GestureParameters, GestureResult]) -> None:
        self._arrive = arrive
        self._standing: Optional[VoidCallback] = None

    @property
    def in_flight(self) -> bool:
        """Whether a conversation of this gesture is under way, from the moment it is asked for to its end."""
        return self._standing is not None

    @abstractmethod
    def __call__(self, *args: GestureParameters.args, **kwargs: GestureParameters.kwargs) -> None:
        """Asks for the gesture with these arguments."""

    def _request(self, *args: GestureParameters.args, **kwargs: GestureParameters.kwargs) -> VoidCallback:
        """The gesture's arrival with these arguments, which discards what the gesture returns."""

        def arrival() -> None:
            self._arrive(*args, **kwargs)

        return arrival

    def _take_off(self, gates: Sequence[Gate], request: VoidCallback) -> None:
        """Asks ``gates`` with ``request`` standing, and holds the flight until they let it through or turn it away."""
        self._standing = request
        asked = False
        try:
            pass_gates(gates, self._land, self._turn_away)
            asked = True
        finally:
            if not asked:
                self._turn_away()

    def _redirect(self, request: VoidCallback) -> None:
        """Lets ``request`` through at the end of the flight under way, in the place of the one standing."""
        self._standing = request

    def _land(self) -> None:
        """Ends the flight, and then lets the request standing through, so its arrival may ask anew."""
        request = self._standing
        assert request is not None, "A conversation let its gesture through after its flight had ended"
        self._standing = None
        request()

    def _turn_away(self) -> None:
        self._standing = None


class LatestRequestFlight(SingleFlight[GestureParameters]):
    """A gesture whose conversation is the same whatever it carries, letting the latest request through.

    The gates are asked once for the whole flight, and a request made meanwhile takes the place of the
    one standing. The answer therefore goes on with what the reader asked for last, such as the second
    of two files opened before the question showed.
    """

    def __init__(
        self,
        gates: Sequence[Gate],
        arrive: Callable[GestureParameters, GestureResult],
    ) -> None:
        super().__init__(arrive)
        self._gates = tuple(gates)

    def __call__(self, *args: GestureParameters.args, **kwargs: GestureParameters.kwargs) -> None:
        request = self._request(*args, **kwargs)
        if self.in_flight:
            self._redirect(request)
            return

        self._take_off(self._gates, request)


class FirstRequestFlight(SingleFlight[GestureParameters]):
    """A gesture whose conversation speaks of what it carries, keeping the first request to the end.

    The conversation is built from the request's arguments, so a question can name the file it asks
    about, and its answer holds for that request alone. A request made while the question stands is
    therefore absorbed, and one made after the answer asks about what it carries.
    """

    def __init__(
        self,
        conversation: Callable[GestureParameters, Sequence[Gate]],
        arrive: Callable[GestureParameters, GestureResult],
    ) -> None:
        super().__init__(arrive)
        self._conversation = conversation

    def __call__(self, *args: GestureParameters.args, **kwargs: GestureParameters.kwargs) -> None:
        if self.in_flight:
            return

        self._take_off(self._conversation(*args, **kwargs), self._request(*args, **kwargs))
