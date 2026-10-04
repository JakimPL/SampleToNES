from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, List, Optional, Sequence, Tuple

import pytest

from sampletones_application.utils.callbacks.gates import (
    FirstRequestFlight,
    Gate,
    LatestRequestFlight,
    SingleFlight,
    asking,
    gated,
    pass_gates,
    waiting,
)
from sampletones_shared.types.callback import VoidCallback
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

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


class TestAQuestionAskedOnTheScreen:
    """A question waits for the screen, and reads what it asks about once the screen is free for it.

    The thing asked about is a guard's own state: ``unfinished`` decides whether there is anything to ask.
    """

    @pytest.fixture(name="screen")
    def screen_fixture(self) -> HeldWait:
        return HeldWait()

    @pytest.fixture(name="question")
    def question_fixture(self, reached: List[str]) -> Guard:
        return Guard("question", reached, unfinished=True)

    @staticmethod
    def ask(question: Guard, screen: HeldWait, reached: List[str]) -> None:
        pass_gates(
            (asking(lambda: question.unfinished, question, screen),),
            lambda: reached.append(ARRIVED),
            lambda: reached.append(DECLINED),
        )

    def test_nothing_unfinished_goes_on_while_the_screen_is_taken(
        self,
        question: Guard,
        screen: HeldWait,
        reached: List[str],
    ) -> None:
        question.unfinished = False

        self.ask(question, screen, reached)

        assert reached == [ARRIVED]

    def test_a_question_waits_for_the_screen(self, question: Guard, screen: HeldWait, reached: List[str]) -> None:
        self.ask(question, screen, reached)

        assert reached == []
        assert not question.is_asking

    def test_a_question_asks_once_the_screen_is_free(
        self,
        question: Guard,
        screen: HeldWait,
        reached: List[str],
    ) -> None:
        self.ask(question, screen, reached)

        screen.release()

        assert reached == ["question"]
        assert question.is_asking

    def test_a_thing_settled_while_the_screen_was_taken_asks_nothing(
        self,
        question: Guard,
        screen: HeldWait,
        reached: List[str],
    ) -> None:
        """A project another conversation closed meanwhile lets the request through with no question."""
        self.ask(question, screen, reached)

        question.unfinished = False
        screen.release()

        assert reached == [ARRIVED]
        assert not question.is_asking

    def test_the_answer_reaches_whoever_asked(self, question: Guard, screen: HeldWait, reached: List[str]) -> None:
        self.ask(question, screen, reached)
        screen.release()

        question.cancel()

        assert reached == ["question", DECLINED]

    def test_a_question_that_fails_on_the_free_screen_turns_the_request_away(
        self,
        screen: HeldWait,
        reached: List[str],
    ) -> None:
        """The failure goes on up from the turn, and whoever waits on the request hears it ended."""

        def broken(_proceed: VoidCallback, _decline: VoidCallback) -> None:
            raise RuntimeError("the question could not be asked")

        pass_gates(
            (asking(lambda: True, broken, screen),),
            lambda: reached.append(ARRIVED),
            lambda: reached.append(DECLINED),
        )

        with pytest.raises(RuntimeError):
            screen.release()

        assert reached == [DECLINED]

    def test_a_reading_that_fails_on_the_free_screen_turns_the_request_away(
        self,
        question: Guard,
        screen: HeldWait,
        reached: List[str],
    ) -> None:
        readings = [True]

        def unsettled() -> bool:
            if not readings:
                raise RuntimeError("the state could not be read")

            return readings.pop()

        pass_gates(
            (asking(unsettled, question, screen),),
            lambda: reached.append(ARRIVED),
            lambda: reached.append(DECLINED),
        )

        with pytest.raises(RuntimeError):
            screen.release()

        assert reached == [DECLINED]
        assert not question.is_asking

    def test_a_failure_after_the_answer_reaches_whoever_asked_once(
        self,
        screen: HeldWait,
        reached: List[str],
    ) -> None:
        """A question that went on before it failed has handed the request over, so nothing declines it again."""

        def going_on_then_failing(proceed: VoidCallback, _decline: VoidCallback) -> None:
            proceed()
            raise RuntimeError("the question failed after it went on")

        pass_gates(
            (asking(lambda: True, going_on_then_failing, screen),),
            lambda: reached.append(ARRIVED),
            lambda: reached.append(DECLINED),
        )

        with pytest.raises(RuntimeError):
            screen.release()

        assert reached == [ARRIVED]


class RaisingOnce:
    """A gate that fails the first time it is reached and lets every later request through."""

    def __init__(self, reached: List[str]) -> None:
        self._reached = reached
        self._raised = False

    def __call__(self, proceed: VoidCallback, _decline: VoidCallback) -> None:
        self._reached.append("broken")
        if not self._raised:
            self._raised = True
            raise RuntimeError("the question could not be asked")

        proceed()


class Answers:
    """A gate that asks each time it is reached and keeps every pair of answers it was handed, stale ones included."""

    def __init__(self) -> None:
        self.handed: List[Tuple[VoidCallback, VoidCallback]] = []

    def __call__(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        self.handed.append((proceed, decline))


def latest_request(gates: Sequence[Gate], arrive: VoidCallback) -> SingleFlight[[]]:
    return LatestRequestFlight(gates, arrive)


def first_request(gates: Sequence[Gate], arrive: VoidCallback) -> SingleFlight[[]]:
    return FirstRequestFlight(lambda: gates, arrive)


class TestEitherFlight(BaseTestSuite):
    """A gesture holds one conversation at a time, whichever request its end lets through.

    The flight ends when the gates let the gesture through or turn it away, so a gesture asked for
    after either asks again.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        build: Callable[[Sequence[Gate], VoidCallback], SingleFlight[[]]]

    test_cases = (
        TestCase(label="latest_request", build=latest_request),
        TestCase(label="first_request", build=first_request),
    )

    @pytest.fixture(name="guard")
    def guard_fixture(self, reached: List[str]) -> Guard:
        return Guard("question", reached, unfinished=True)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_two_requests_ask_once(self, test_case: TestCase, guard: Guard, reached: List[str]) -> None:
        flight = test_case.build((guard,), lambda: reached.append(ARRIVED))

        flight()
        flight()

        assert reached == ["question"]
        assert flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_answer_arrives_once(self, test_case: TestCase, guard: Guard, reached: List[str]) -> None:
        flight = test_case.build((guard,), lambda: reached.append(ARRIVED))
        flight()
        flight()

        guard.answer()

        assert reached == ["question", ARRIVED]
        assert not flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_request_after_an_arrival_asks_again(
        self,
        test_case: TestCase,
        guard: Guard,
        reached: List[str],
    ) -> None:
        flight = test_case.build((guard,), lambda: reached.append(ARRIVED))
        flight()
        guard.answer()

        flight()

        assert reached == ["question", ARRIVED, "question"]
        assert flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_request_after_a_decline_asks_again(
        self,
        test_case: TestCase,
        guard: Guard,
        reached: List[str],
    ) -> None:
        flight = test_case.build((guard,), lambda: reached.append(ARRIVED))
        flight()
        guard.cancel()
        assert not flight.in_flight

        flight()

        assert reached == ["question", "question"]
        assert guard.is_asking

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_two_requests_while_a_wait_holds_the_gesture_ask_once(
        self,
        test_case: TestCase,
        guard: Guard,
        reached: List[str],
    ) -> None:
        wait = HeldWait()
        flight = test_case.build((waiting(wait), guard), lambda: reached.append(ARRIVED))

        flight()
        flight()
        wait.release()

        assert reached == ["question"]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_gesture_with_nothing_to_ask_arrives_and_lands(self, test_case: TestCase, reached: List[str]) -> None:
        flight = test_case.build((Guard("clear", reached, unfinished=False),), lambda: reached.append(ARRIVED))

        flight()
        flight()

        assert reached == ["clear", ARRIVED, "clear", ARRIVED]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_gate_that_raises_ends_the_flight(self, test_case: TestCase, reached: List[str]) -> None:
        def broken(_proceed: VoidCallback, _decline: VoidCallback) -> None:
            reached.append("broken")
            raise RuntimeError("the question could not be asked")

        flight = test_case.build((broken,), lambda: reached.append(ARRIVED))

        with pytest.raises(RuntimeError):
            flight()

        assert not flight.in_flight
        with pytest.raises(RuntimeError):
            flight()
        assert reached == ["broken", "broken"]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_raise_once_the_wait_lets_go_ends_the_flight(self, test_case: TestCase, reached: List[str]) -> None:
        """The edits landing run the rest of the conversation, and a failure there leaves the gesture to ask again."""
        wait = HeldWait()
        flight = test_case.build((waiting(wait), RaisingOnce(reached)), lambda: reached.append(ARRIVED))
        flight()

        with pytest.raises(RuntimeError):
            wait.release()

        assert not flight.in_flight
        flight()
        assert flight.in_flight
        wait.release()
        assert reached == ["broken", "broken", ARRIVED]
        assert not flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_raise_once_the_question_is_answered_ends_the_flight(
        self,
        test_case: TestCase,
        guard: Guard,
        reached: List[str],
    ) -> None:
        """An answer runs the rest of the conversation, and a failure there leaves the gesture to ask again."""
        flight = test_case.build((guard, RaisingOnce(reached)), lambda: reached.append(ARRIVED))
        flight()

        with pytest.raises(RuntimeError):
            guard.answer()

        assert not flight.in_flight
        flight()
        assert guard.is_asking
        guard.answer()
        assert reached == ["question", "broken", "question", "broken", ARRIVED]
        assert not flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_raise_once_the_screen_is_free_ends_the_flight(self, test_case: TestCase, reached: List[str]) -> None:
        """A question waiting for the screen fails as it is asked there, and the gesture asks again when asked for."""
        screen = HeldWait()
        flight = test_case.build(
            (asking(lambda: True, RaisingOnce(reached), screen),),
            lambda: reached.append(ARRIVED),
        )
        flight()

        with pytest.raises(RuntimeError):
            screen.release()

        assert not flight.in_flight
        flight()
        assert flight.in_flight
        screen.release()
        assert reached == ["broken", "broken", ARRIVED]
        assert not flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_stale_answer_going_on_leaves_the_newer_flight_standing(
        self,
        test_case: TestCase,
        reached: List[str],
    ) -> None:
        """An answer handed to a conversation that has ended reaches nothing the newer one holds."""
        answers = Answers()
        flight = test_case.build((answers,), lambda: reached.append(ARRIVED))
        flight()
        stale_proceed, stale_decline = answers.handed[0]
        stale_decline()
        flight()

        stale_proceed()

        assert flight.in_flight
        assert reached == []
        newer_proceed, _ = answers.handed[1]
        newer_proceed()
        assert reached == [ARRIVED]
        assert not flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_stale_answer_turning_away_leaves_the_newer_flight_standing(
        self,
        test_case: TestCase,
        reached: List[str],
    ) -> None:
        answers = Answers()
        flight = test_case.build((answers,), lambda: reached.append(ARRIVED))
        flight()
        stale_proceed, stale_decline = answers.handed[0]
        stale_proceed()
        flight()

        stale_decline()

        assert flight.in_flight
        newer_proceed, _ = answers.handed[1]
        newer_proceed()
        assert reached == [ARRIVED, ARRIVED]
        assert not flight.in_flight

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_an_arrival_that_asks_again_and_raises_keeps_the_newer_flight(
        self,
        test_case: TestCase,
        reached: List[str],
    ) -> None:
        """A gesture whose arrival asks for it again and then fails leaves the question it asked standing."""
        guard = Guard("question", reached, unfinished=False)

        def arrive() -> None:
            reached.append(ARRIVED)
            guard.unfinished = True
            flight()
            raise RuntimeError("the arrival failed after asking again")

        flight = test_case.build((guard,), arrive)

        with pytest.raises(RuntimeError):
            flight()

        assert flight.in_flight
        assert guard.is_asking
        assert reached == ["question", ARRIVED, "question"]


class TestLatestRequestFlight:
    """A conversation that is the same whatever the gesture carries lets the latest request through.

    The question is asked once for the whole flight, a decline drops every request made during it, and
    a request made after the flight ended asks again with what it carries.
    """

    @pytest.fixture(name="guard")
    def guard_fixture(self, reached: List[str]) -> Guard:
        return Guard("question", reached, unfinished=True)

    @pytest.fixture(name="opened")
    def opened_fixture(self) -> List[Path]:
        return []

    @pytest.fixture(name="flight")
    def flight_fixture(self, guard: Guard, opened: List[Path]) -> LatestRequestFlight[[Path]]:
        return LatestRequestFlight((guard,), opened.append)

    def test_the_answer_goes_on_with_the_latest_request(
        self,
        flight: LatestRequestFlight[[Path]],
        guard: Guard,
        reached: List[str],
        opened: List[Path],
    ) -> None:
        flight(Path("first.stn"))
        flight(Path("second.stn"))
        flight(Path("third.stn"))

        guard.answer()

        assert reached == ["question"]
        assert opened == [Path("third.stn")]

    def test_a_request_made_while_a_wait_holds_the_gesture_arrives(
        self,
        guard: Guard,
        reached: List[str],
        opened: List[Path],
    ) -> None:
        """Two files opened while the edits are on their way ask once, and the answer opens the second."""
        wait = HeldWait()
        flight: LatestRequestFlight[[Path]] = LatestRequestFlight((waiting(wait), guard), opened.append)
        flight(Path("drums.stn"))
        flight(Path("bass.stn"))
        wait.release()

        guard.answer()

        assert reached == ["question"]
        assert opened == [Path("bass.stn")]

    def test_a_decline_drops_every_request_of_the_flight(
        self,
        flight: LatestRequestFlight[[Path]],
        guard: Guard,
        reached: List[str],
        opened: List[Path],
    ) -> None:
        flight(Path("first.stn"))
        flight(Path("second.stn"))
        guard.cancel()

        flight(Path("third.stn"))
        guard.answer()

        assert reached == ["question", "question"]
        assert opened == [Path("third.stn")]

    def test_a_request_after_the_arrival_starts_a_new_conversation(
        self,
        flight: LatestRequestFlight[[Path]],
        guard: Guard,
        reached: List[str],
        opened: List[Path],
    ) -> None:
        flight(Path("first.stn"))
        guard.answer()

        flight(Path("second.stn"))
        assert opened == [Path("first.stn")]
        guard.answer()

        assert reached == ["question", "question"]
        assert opened == [Path("first.stn"), Path("second.stn")]

    def test_a_gate_that_raises_drops_its_request(self, reached: List[str], opened: List[Path]) -> None:
        flight: LatestRequestFlight[[Path]] = LatestRequestFlight((RaisingOnce(reached),), opened.append)
        with pytest.raises(RuntimeError):
            flight(Path("first.stn"))

        flight(Path("second.stn"))

        assert reached == ["broken", "broken"]
        assert opened == [Path("second.stn")]


class TestFirstRequestFlight:
    """A conversation built from the request keeps the first request, so the answer holds for what it asked about.

    A request made while the question stands is absorbed, and one made after the answer asks about
    what it carries.
    """

    def test_the_answer_goes_on_with_the_first_request(self, reached: List[str]) -> None:
        guard = Guard("question", reached, unfinished=True)
        opened: List[Path] = []
        flight: FirstRequestFlight[[Path]] = FirstRequestFlight(lambda _path: (guard,), opened.append)

        flight(Path("first.stn"))
        flight(Path("second.stn"))
        guard.answer()

        assert reached == ["question"]
        assert opened == [Path("first.stn")]

    def test_the_question_is_built_from_the_gesture_that_asked(self, reached: List[str]) -> None:
        """A question speaking of what the gesture asks for is built from that gesture's arguments."""
        guards: List[Guard] = []

        def conversation(path: Path) -> List[Gate]:
            guard = Guard(path.name, reached, unfinished=True)
            guards.append(guard)
            return [guard]

        opened: List[Path] = []
        flight: FirstRequestFlight[[Path]] = FirstRequestFlight(conversation, opened.append)

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

        flight: FirstRequestFlight[[]] = FirstRequestFlight(conversation, lambda: reached.append(ARRIVED))

        with pytest.raises(RuntimeError):
            flight()

        assert not flight.in_flight
        assert not reached
