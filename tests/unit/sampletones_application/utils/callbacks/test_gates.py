from pathlib import Path
from typing import Final, List, Optional

import pytest

from sampletones_application.utils.callbacks.gates import Gate, SingleFlight, fixed, gated, pass_gates, waiting
from sampletones_shared.types.callback import VoidCallback

ARRIVED: Final[str] = "arrived"
DECLINED: Final[str] = "declined"


class Guard:
    """A gate over one unfinished thing, recording when it is reached and holding its question."""

    def __init__(self, name: str, reached: List[str], *, unfinished: bool) -> None:
        self.name = name
        self.unfinished = unfinished
        self._reached = reached
        self._proceed: Optional[VoidCallback] = None
        self._decline: Optional[VoidCallback] = None

    def __call__(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        self._reached.append(self.name)
        if not self.unfinished:
            proceed()
            return

        self._proceed = proceed
        self._decline = decline

    @property
    def is_asking(self) -> bool:
        return self._proceed is not None

    def answer(self) -> None:
        """The reader going on past the question this gate asked."""
        assert self._proceed is not None
        proceed = self._proceed
        self._proceed, self._decline = None, None
        proceed()

    def cancel(self) -> None:
        """The reader turning the request away at the question this gate asked."""
        assert self._decline is not None
        decline = self._decline
        self._proceed, self._decline = None, None
        decline()


class HeldWait:
    """A wait a case lets go of by hand, the way the open reconstruction's edits hold a gesture until they land."""

    def __init__(self) -> None:
        self._held: List[VoidCallback] = []

    def __call__(self, proceed: VoidCallback) -> None:
        self._held.append(proceed)

    def release(self) -> None:
        held, self._held = self._held, []
        for proceed in held:
            proceed()


@pytest.fixture(name="reached")
def reached_fixture() -> List[str]:
    return []


class TestPassingGates:
    def test_no_gate_arrives_at_once(self, reached: List[str]) -> None:
        pass_gates((), lambda: reached.append(ARRIVED), lambda: reached.append(DECLINED))

        assert reached == [ARRIVED]

    def test_open_gates_are_passed_in_order(self, reached: List[str]) -> None:
        gates = [Guard(name, reached, unfinished=False) for name in ("first", "second", "third")]

        pass_gates(gates, lambda: reached.append(ARRIVED), lambda: reached.append(DECLINED))

        assert reached == ["first", "second", "third", ARRIVED]

    def test_a_question_holds_the_gates_after_it(self, reached: List[str]) -> None:
        asking = Guard("first", reached, unfinished=True)

        pass_gates(
            (asking, Guard("second", reached, unfinished=False)),
            lambda: reached.append(ARRIVED),
            lambda: reached.append(DECLINED),
        )

        assert reached == ["first"]

    def test_an_answer_goes_on_to_the_next_gate(self, reached: List[str]) -> None:
        asking = Guard("first", reached, unfinished=True)
        pass_gates(
            (asking, Guard("second", reached, unfinished=False)),
            lambda: reached.append(ARRIVED),
            lambda: reached.append(DECLINED),
        )

        asking.answer()

        assert reached == ["first", "second", ARRIVED]

    def test_a_declined_question_runs_the_decline_alone(self, reached: List[str]) -> None:
        """The gates after a declined question and the arrival stay unreached, and the decline says so."""
        first = Guard("first", reached, unfinished=True)
        second = Guard("second", reached, unfinished=True)
        third = Guard("third", reached, unfinished=False)
        pass_gates((first, second, third), lambda: reached.append(ARRIVED), lambda: reached.append(DECLINED))

        first.answer()
        second.cancel()

        assert reached == ["first", "second", DECLINED]

    def test_a_gate_reads_what_it_guards_when_it_is_reached(self, reached: List[str]) -> None:
        """A state an earlier question saw settled meanwhile asks nothing once its gate is reached."""
        asking = Guard("first", reached, unfinished=True)
        later = Guard("second", reached, unfinished=True)
        pass_gates((asking, later), lambda: reached.append(ARRIVED), lambda: reached.append(DECLINED))

        later.unfinished = False
        asking.answer()

        assert reached == ["first", "second", ARRIVED]
        assert not later.is_asking


class TestAWaitAsAGate:
    def test_a_waiting_gate_holds_the_request_until_the_wait_ends(self, reached: List[str]) -> None:
        wait = HeldWait()

        pass_gates((waiting(wait),), lambda: reached.append(ARRIVED), lambda: reached.append(DECLINED))
        assert reached == []

        wait.release()

        assert reached == [ARRIVED]

    def test_a_gated_gesture_runs_with_its_arguments_once_the_wait_ends(self) -> None:
        wait = HeldWait()
        opened: List[Path] = []
        gesture = gated(wait, opened.append)

        gesture(Path("song.stp"))
        assert opened == []

        wait.release()

        assert opened == [Path("song.stp")]


class TestSingleFlight:
    """A gesture holds one conversation at a time: a repeat while it is in flight is absorbed.

    The flight ends when the gates let the gesture through or turn it away, so a gesture asked for
    after either asks again.
    """

    @pytest.fixture(name="guard")
    def guard_fixture(self, reached: List[str]) -> Guard:
        return Guard("question", reached, unfinished=True)

    @pytest.fixture(name="flight")
    def flight_fixture(self, guard: Guard, reached: List[str]) -> SingleFlight[[]]:
        return SingleFlight(fixed((guard,)), lambda: reached.append(ARRIVED))

    def test_a_repeat_while_the_question_stands_is_absorbed(
        self,
        flight: SingleFlight[[]],
        reached: List[str],
    ) -> None:
        flight()
        flight()

        assert reached == ["question"]
        assert flight.in_flight

    def test_the_absorbed_repeat_arrives_once(
        self,
        flight: SingleFlight[[]],
        guard: Guard,
        reached: List[str],
    ) -> None:
        flight()
        flight()

        guard.answer()

        assert reached == ["question", ARRIVED]
        assert not flight.in_flight

    def test_a_gesture_after_an_arrival_asks_again(
        self,
        flight: SingleFlight[[]],
        guard: Guard,
        reached: List[str],
    ) -> None:
        flight()
        guard.answer()

        flight()

        assert reached == ["question", ARRIVED, "question"]
        assert flight.in_flight

    def test_a_gesture_after_a_decline_asks_again(
        self,
        flight: SingleFlight[[]],
        guard: Guard,
        reached: List[str],
    ) -> None:
        flight()
        guard.cancel()
        assert not flight.in_flight

        flight()

        assert reached == ["question", "question"]
        assert guard.is_asking

    def test_a_repeat_while_a_wait_holds_the_gesture_is_absorbed(self, reached: List[str]) -> None:
        wait = HeldWait()
        guard = Guard("question", reached, unfinished=True)
        flight: SingleFlight[[]] = SingleFlight(fixed((waiting(wait), guard)), lambda: reached.append(ARRIVED))

        flight()
        flight()
        wait.release()

        assert reached == ["question"]

    def test_the_arrival_takes_the_arguments_of_the_gesture_that_asked(self, reached: List[str]) -> None:
        guard = Guard("question", reached, unfinished=True)
        opened: List[Path] = []
        flight: SingleFlight[[Path]] = SingleFlight(fixed((guard,)), opened.append)

        flight(Path("first.stn"))
        flight(Path("second.stn"))
        guard.answer()

        assert opened == [Path("first.stn")]

    def test_the_question_is_built_from_the_gesture_that_asked(self, reached: List[str]) -> None:
        """A question speaking of what the gesture asks for is built from that gesture's arguments."""
        guards: List[Guard] = []

        def conversation(path: Path) -> List[Gate]:
            guard = Guard(path.name, reached, unfinished=True)
            guards.append(guard)
            return [guard]

        opened: List[Path] = []
        flight: SingleFlight[[Path]] = SingleFlight(conversation, opened.append)

        flight(Path("first.stn"))
        flight(Path("second.stn"))
        guards[0].answer()
        flight(Path("third.stn"))

        assert reached == ["first.stn", "third.stn"]
        assert opened == [Path("first.stn")]
        assert flight.in_flight

    def test_a_conversation_that_raises_ends_the_flight(self, reached: List[str]) -> None:
        def conversation() -> List[Gate]:
            raise RuntimeError("the question could not be built")

        flight: SingleFlight[[]] = SingleFlight(conversation, lambda: reached.append(ARRIVED))

        with pytest.raises(RuntimeError):
            flight()

        assert not flight.in_flight
        assert not reached

    def test_a_gesture_with_nothing_to_ask_arrives_and_lands(self, reached: List[str]) -> None:
        flight: SingleFlight[[]] = SingleFlight(
            fixed((Guard("clear", reached, unfinished=False),)),
            lambda: reached.append(ARRIVED),
        )

        flight()
        flight()

        assert reached == ["clear", ARRIVED, "clear", ARRIVED]

    def test_a_gate_that_raises_ends_the_flight(self, reached: List[str]) -> None:
        def broken(_proceed: VoidCallback, _decline: VoidCallback) -> None:
            reached.append("broken")
            raise RuntimeError("the question could not be asked")

        flight: SingleFlight[[]] = SingleFlight(fixed((broken,)), lambda: reached.append(ARRIVED))

        with pytest.raises(RuntimeError):
            flight()

        assert not flight.in_flight
        with pytest.raises(RuntimeError):
            flight()
        assert reached == ["broken", "broken"]
