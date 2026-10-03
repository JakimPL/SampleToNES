from typing import Final, Iterator, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.application import Application
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_shared.types.callback import VoidCallback

PROJECT: Final[str] = "project"
RECONSTRUCTION: Final[str] = "reconstruction"
CONVERSION: Final[str] = "conversion"
LIBRARY: Final[str] = "library"
OWNERS: Final[Tuple[str, ...]] = (PROJECT, RECONSTRUCTION, CONVERSION, LIBRARY)


class Owner:
    """One owner of something the exit asks about, answering the way a real prompt would."""

    def __init__(self, name: str, asked: List[str]) -> None:
        self.name = name
        self.unfinished = False
        self.editing = False
        self._asked = asked
        self._proceed: Optional[VoidCallback] = None
        self._decline: Optional[VoidCallback] = None
        self._after_edits: List[VoidCallback] = []

    def after_edits(self, gesture: VoidCallback) -> None:
        """Holds the gesture while an edit is on its way, in line, the way the reconstruction's rewrites do."""
        if not self.editing:
            gesture()
            return

        self._after_edits.append(gesture)

    def land(self) -> None:
        """The edit on its way landing, which lets every gesture waiting on it run in the order it came."""
        assert self._after_edits
        gestures, self._after_edits = self._after_edits, []
        self.editing = False
        for gesture in gestures:
            gesture()

    def guard_exit(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        if not self.unfinished:
            proceed()
            return

        self._asked.append(self.name)
        self._proceed = proceed
        self._decline = decline

    @property
    def is_asking(self) -> bool:
        return self._proceed is not None

    def go_on(self) -> None:
        """The reader answering the question with Save, Exit or Discard."""
        assert self._proceed is not None
        proceed = self._proceed
        self._proceed, self._decline = None, None
        proceed()

    def cancel(self) -> None:
        """The reader answering the question with Cancel, which turns the exit away."""
        assert self._decline is not None
        decline = self._decline
        self._proceed, self._decline = None, None
        decline()


class Exiting:
    """An application whose owners ask about what they hold, and whose exit is only recorded."""

    def __init__(self) -> None:
        self.asked: List[str] = []
        self.owners = {name: Owner(name, self.asked) for name in OWNERS}
        self.application = Application.__new__(Application)
        self.application._project_coordinator = self.owners[PROJECT]
        self.application._reconstruction_coordinator = self.owners[RECONSTRUCTION]
        self.application._main_tab = self.owners[CONVERSION]
        self.application._instructions_tab = self.owners[LIBRARY]
        self.exit = MagicMock()
        self.application._exit_application = self.exit
        self.application._exiting = self.application._exit_flight()

    def unfinished(self, *names: str) -> None:
        for name in names:
            self.owners[name].unfinished = True

    def close(self) -> None:
        self.application._exiting()


@pytest.fixture(name="exiting")
def exiting_fixture() -> Exiting:
    return Exiting()


class TestExitingWithNothingUnfinished:
    def test_the_application_exits_at_once(self, exiting: Exiting) -> None:
        exiting.close()

        exiting.exit.assert_called_once_with()
        assert exiting.asked == []


class TestExitingWithEverythingUnfinished:
    """Each owner asks in turn, and the application exits once the last one lets it go."""

    @pytest.fixture(name="closing")
    def closing_fixture(self, exiting: Exiting) -> Exiting:
        exiting.unfinished(*OWNERS)
        exiting.close()
        return exiting

    def test_the_project_asks_first(self, closing: Exiting) -> None:
        assert closing.asked == [PROJECT]
        closing.exit.assert_not_called()

    def test_its_answer_leads_to_the_reconstruction_question(self, closing: Exiting) -> None:
        closing.owners[PROJECT].go_on()

        assert closing.asked == [PROJECT, RECONSTRUCTION]
        closing.exit.assert_not_called()

    def test_every_owner_is_asked_in_turn(self, closing: Exiting) -> None:
        for name in OWNERS:
            closing.owners[name].go_on()

        assert closing.asked == list(OWNERS)
        closing.exit.assert_called_once_with()

    def test_canceling_any_question_keeps_the_application_open(self, closing: Exiting) -> None:
        closing.owners[PROJECT].go_on()
        closing.owners[RECONSTRUCTION].cancel()

        assert closing.asked == [PROJECT, RECONSTRUCTION]
        closing.exit.assert_not_called()


class TestAStateSettledWhileAQuestionStood:
    """An owner reads what it holds when the exit reaches it, so a job ending while the project
    question stands is asked about no more."""

    def test_a_finished_conversion_asks_nothing(self, exiting: Exiting) -> None:
        exiting.unfinished(PROJECT, CONVERSION)
        exiting.close()

        exiting.owners[CONVERSION].unfinished = False
        exiting.owners[PROJECT].go_on()

        assert exiting.asked == [PROJECT]
        exiting.exit.assert_called_once_with()


class TestEachOwnerAlone:
    """Whichever owner holds something unfinished, its answer is what reaches the exit."""

    @pytest.mark.parametrize("name", OWNERS)
    def test_going_on_exits(self, exiting: Exiting, name: str) -> None:
        exiting.unfinished(name)
        exiting.close()

        exiting.owners[name].go_on()

        assert exiting.asked == [name]
        exiting.exit.assert_called_once_with()

    @pytest.mark.parametrize("name", OWNERS)
    def test_canceling_stays(self, exiting: Exiting, name: str) -> None:
        exiting.unfinished(name)
        exiting.close()

        exiting.owners[name].cancel()

        exiting.exit.assert_not_called()


class TestExitingWhileAnEditIsOnItsWay:
    """The exit waits for the edits of the open reconstruction first, so every question asks about what the reader drew."""

    def test_nothing_is_asked_before_the_edit_lands(self, exiting: Exiting) -> None:
        exiting.owners[RECONSTRUCTION].editing = True
        exiting.unfinished(PROJECT)

        exiting.close()

        assert exiting.asked == []
        exiting.exit.assert_not_called()

    def test_the_questions_follow_once_it_lands(self, exiting: Exiting) -> None:
        exiting.owners[RECONSTRUCTION].editing = True
        exiting.unfinished(PROJECT)
        exiting.close()

        exiting.owners[RECONSTRUCTION].land()

        assert exiting.asked == [PROJECT]

    def test_the_application_exits_once_it_lands_with_nothing_unfinished(self, exiting: Exiting) -> None:
        exiting.owners[RECONSTRUCTION].editing = True
        exiting.close()

        exiting.owners[RECONSTRUCTION].land()

        exiting.exit.assert_called_once_with()


class TestClosingTwiceBeforeTheAnswer:
    """A close asked for again while the exit's questions stand is absorbed, and Cancel ends the exit.

    A close made after the answer asks again, so the reader can always leave.
    """

    def test_two_closes_over_a_question_ask_once(self, exiting: Exiting) -> None:
        exiting.unfinished(PROJECT)

        exiting.close()
        exiting.close()

        assert exiting.asked == [PROJECT]

    def test_cancel_leaves_no_question_behind(self, exiting: Exiting) -> None:
        exiting.unfinished(PROJECT)
        exiting.close()
        exiting.close()

        exiting.owners[PROJECT].cancel()

        assert not exiting.owners[PROJECT].is_asking
        assert exiting.asked == [PROJECT]
        exiting.exit.assert_not_called()

    def test_a_close_after_cancel_asks_again(self, exiting: Exiting) -> None:
        exiting.unfinished(PROJECT)
        exiting.close()
        exiting.owners[PROJECT].cancel()

        exiting.close()
        exiting.owners[PROJECT].go_on()

        assert exiting.asked == [PROJECT, PROJECT]
        exiting.exit.assert_called_once_with()

    def test_a_close_while_a_later_question_stands_is_absorbed(self, exiting: Exiting) -> None:
        exiting.unfinished(PROJECT, CONVERSION)
        exiting.close()
        exiting.owners[PROJECT].go_on()

        exiting.close()

        assert exiting.asked == [PROJECT, CONVERSION]

    def test_two_closes_while_an_edit_is_on_its_way_ask_once_it_lands(self, exiting: Exiting) -> None:
        exiting.owners[RECONSTRUCTION].editing = True
        exiting.unfinished(RECONSTRUCTION)
        exiting.close()
        exiting.close()

        exiting.owners[RECONSTRUCTION].land()

        assert exiting.asked == [RECONSTRUCTION]


class TestTheFrameTheExitIsDecidedIn:
    """The work waiting on the render thread stays unrun once the exit is decided, so nothing the reader
    left behind starts after they chose to leave."""

    @pytest.fixture(autouse=True)
    def live_queue(self) -> Iterator[None]:
        CallbackQueue.start()
        yield
        CallbackQueue.stop()
        CallbackQueue.start()

    def test_the_work_due_in_that_frame_stays_unrun(self) -> None:
        application = Application.__new__(Application)
        ran: List[str] = []
        CallbackQueue.add(lambda: ran.append("late"))

        with patch("dearpygui.dearpygui.stop_dearpygui") as stop_dearpygui:
            application._exit_application()
        CallbackQueue.process(budget_seconds=1.0)

        stop_dearpygui.assert_called_once_with()
        assert not ran

    def test_the_work_due_before_the_exit_runs(self) -> None:
        ran: List[str] = []
        CallbackQueue.add(lambda: ran.append("due"))

        CallbackQueue.process(budget_seconds=1.0)

        assert ran == ["due"]
