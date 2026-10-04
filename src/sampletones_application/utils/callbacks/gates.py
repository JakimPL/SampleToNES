from abc import ABC, abstractmethod
from dataclasses import dataclass
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


def asking(
    unsettled: Callable[[], bool],
    question: Gate,
    screen: Wait,
) -> Gate:
    """A gate that asks ``question`` about something unsettled once ``screen`` is free for the question.

    While ``unsettled`` reads false, the request goes on at once, whatever holds the screen. Otherwise
    the gate waits for the screen and reads ``unsettled`` again there, so the question speaks of the
    state it shows over. A thing another conversation settled meanwhile, such as a project its answer
    closed, lets the request through with no question.

    Args:
        unsettled: Whether there is something to ask about.
        question: The gate that asks, which runs only while the screen is free for it.
        screen: The wait for the screen, such as the modal line's turn.
    """

    def gate(proceed: VoidCallback, decline: VoidCallback) -> None:
        if not unsettled():
            proceed()
            return

        def ask_on_the_screen() -> None:
            if unsettled():
                question(proceed, decline)
            else:
                proceed()

        screen(ask_on_the_screen)

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


@dataclass(eq=False)
class Ticket:
    """One take-off of a gesture, and the request its end lets through.

    Each take-off gets a ticket of its own, so a continuation handed out during one conversation
    reaches that conversation alone.

    Attributes:
        request: The gesture's arrival the end of the flight lets through.
    """

    request: VoidCallback


class SingleFlight(ABC, Generic[GestureParameters]):
    """A gesture that holds one conversation at a time, and lets one request through at its end.

    The conversation is the gates the gesture passes. It is in flight from the moment the gesture is
    asked for until the gates let it through or turn it away, and a gesture asked for after that asks
    again. A gesture asked for while it is in flight asks nothing, and the kind of flight decides which
    request its end lets through. A conversation that turns the gesture away drops the request it
    holds. A gate, or a continuation a gate runs after an answer or a wait, that raises ends the
    flight the same way, so one failure leaves the gesture to be asked for again. Each take-off has a
    ticket, and a continuation acts on the flight of its own ticket alone, so an answer reaching a
    conversation that has ended leaves the newer one as it stands.
    """

    def __init__(self, arrive: Callable[GestureParameters, GestureResult]) -> None:
        self._arrive = arrive
        self._ticket: Optional[Ticket] = None

    @property
    def in_flight(self) -> bool:
        """Whether a conversation of this gesture is under way, from the moment it is asked for to its end."""
        return self._ticket is not None

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
        ticket = Ticket(request=request)
        self._ticket = ticket
        conversation = partial(
            pass_gates,
            [self._guarded_gate(ticket, gate) for gate in gates],
            partial(self._land, ticket),
            partial(self._turn_away, ticket),
        )
        self._guarded(ticket, conversation)()

    def _redirect(self, request: VoidCallback) -> None:
        """Lets ``request`` through at the end of the flight under way, in the place of the one standing."""
        assert self._ticket is not None, "A request was redirected with no flight under way"
        self._ticket.request = request

    def _guarded_gate(self, ticket: Ticket, gate: Gate) -> Gate:
        """``gate`` handed continuations that end the flight of ``ticket`` when they raise."""

        def guarded(proceed: VoidCallback, decline: VoidCallback) -> None:
            gate(self._guarded(ticket, proceed), self._guarded(ticket, decline))

        return guarded

    def _guarded(self, ticket: Ticket, continuation: VoidCallback) -> VoidCallback:
        """``continuation`` turning the flight of ``ticket`` away when it raises, with the error going on up."""

        def run() -> None:
            went_on = False
            try:
                continuation()
                went_on = True
            finally:
                if not went_on:
                    self._turn_away(ticket)

        return run

    def _land(self, ticket: Ticket) -> None:
        """Ends the flight of ``ticket``, and then lets its request through, so its arrival may ask anew."""
        if self._ticket is not ticket:
            return

        self._ticket = None
        ticket.request()

    def _turn_away(self, ticket: Ticket) -> None:
        if self._ticket is ticket:
            self._ticket = None


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
