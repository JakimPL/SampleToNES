from typing import List, Optional

from sampletones_application.utils.callbacks.gates import pass_gates
from sampletones_shared.types.callback import VoidCallback


class Guard:
    """A gate over one unfinished thing, recording when it is reached and holding its question."""

    def __init__(self, name: str, reached: List[str], *, unfinished: bool) -> None:
        self.name = name
        self.unfinished = unfinished
        self._reached = reached
        self.question: Optional[VoidCallback] = None

    def __call__(self, proceed: VoidCallback) -> None:
        self._reached.append(self.name)
        if not self.unfinished:
            proceed()
            return

        self.question = proceed

    def answer(self) -> None:
        """The reader going on past the question this gate asked."""
        assert self.question is not None
        question, self.question = self.question, None
        question()


class TestPassingGates:
    def test_no_gate_arrives_at_once(self) -> None:
        arrived: List[str] = []

        pass_gates((), lambda: arrived.append("arrived"))

        assert arrived == ["arrived"]

    def test_open_gates_are_passed_in_order(self) -> None:
        reached: List[str] = []
        gates = [Guard(name, reached, unfinished=False) for name in ("first", "second", "third")]

        pass_gates(gates, lambda: reached.append("arrived"))

        assert reached == ["first", "second", "third", "arrived"]

    def test_a_question_holds_the_gates_after_it(self) -> None:
        reached: List[str] = []
        asking = Guard("first", reached, unfinished=True)

        pass_gates((asking, Guard("second", reached, unfinished=False)), lambda: reached.append("arrived"))

        assert reached == ["first"]

    def test_an_answer_goes_on_to_the_next_gate(self) -> None:
        reached: List[str] = []
        asking = Guard("first", reached, unfinished=True)
        pass_gates((asking, Guard("second", reached, unfinished=False)), lambda: reached.append("arrived"))

        asking.answer()

        assert reached == ["first", "second", "arrived"]

    def test_a_declined_question_arrives_nowhere(self) -> None:
        """Declining answers nothing, so the gates after it and the arrival wait for good."""
        reached: List[str] = []
        first = Guard("first", reached, unfinished=True)
        second = Guard("second", reached, unfinished=True)
        third = Guard("third", reached, unfinished=False)
        pass_gates((first, second, third), lambda: reached.append("arrived"))

        first.answer()

        assert reached == ["first", "second"]

    def test_a_gate_reads_what_it_guards_when_it_is_reached(self) -> None:
        """A state an earlier question saw settled meanwhile asks nothing once its gate is reached."""
        reached: List[str] = []
        asking = Guard("first", reached, unfinished=True)
        later = Guard("second", reached, unfinished=True)
        pass_gates((asking, later), lambda: reached.append("arrived"))

        later.unfinished = False
        asking.answer()

        assert reached == ["first", "second", "arrived"]
        assert later.question is None
