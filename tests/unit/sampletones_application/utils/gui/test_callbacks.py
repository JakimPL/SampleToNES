from dataclasses import dataclass
from typing import Any, Iterator, List, Sequence, Tuple
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.callbacks import hold_callbacks, run_held_callbacks
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SENDER = "the.widget"
APP_DATA = 7
USER_DATA = "carried"
JOB = (SENDER, APP_DATA, USER_DATA)


@pytest.fixture
def dpg_context() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


def held(*jobs: Tuple[Any, ...]) -> Any:
    """Stands in for what DearPyGui hands back, which is a list of jobs or nothing at all."""
    return patch.object(dpg, "get_callback_queue", return_value=list(jobs) or None)


class TestHoldingACallback(BaseTestSuite):
    """A gesture is gathered rather than answered where it lands, so the frame runs it."""

    def test_it_asks_dearpygui_to_gather_them(self, dpg_context: None) -> None:
        hold_callbacks()

        assert dpg.get_app_configuration()["manual_callback_management"]


class TestRunningWhatWasHeld(BaseTestSuite):
    """Each gathered gesture runs on the thread that drew the items it reaches."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        declared: int
        expected: Sequence[Any]

    test_cases = (
        TestCase(label="a_callback_taking_nothing", declared=0, expected=()),
        TestCase(label="a_callback_taking_the_sender", declared=1, expected=(SENDER,)),
        TestCase(label="a_callback_taking_the_payload", declared=2, expected=(SENDER, APP_DATA)),
        TestCase(label="a_callback_taking_the_user_data", declared=3, expected=(SENDER, APP_DATA, USER_DATA)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_callback_is_handed_the_arguments_it_declares(self, test_case: TestCase) -> None:
        received: List[Sequence[Any]] = []
        callback = self._taking(test_case.declared, received)
        with held((callback, *JOB)):
            run_held_callbacks()

        assert received == [tuple(test_case.expected)]

    def test_a_callback_taking_whatever_comes_is_handed_all_of_it(self) -> None:
        received: List[Sequence[Any]] = []

        def callback(*arguments: Any) -> None:
            received.append(arguments)

        with held((callback, *JOB)):
            run_held_callbacks()

        assert received == [JOB]

    def test_a_gesture_without_a_callback_is_passed_over(self) -> None:
        with held((None, *JOB)):
            run_held_callbacks()

    def test_an_empty_queue_leaves_the_frame_alone(self) -> None:
        with held():
            run_held_callbacks()

    def test_a_failing_gesture_leaves_the_rest_to_run(self) -> None:
        """A gesture that raises is reported rather than taking the frame's other gestures down."""
        received: List[Sequence[Any]] = []

        def failing() -> None:
            raise RuntimeError("the gesture went wrong")

        with held((failing, *JOB), (self._taking(0, received), *JOB)):
            run_held_callbacks()

        assert received == [()]

    def test_the_gestures_run_in_the_order_they_were_made(self) -> None:
        order: List[str] = []
        with held(
            (lambda: order.append("first"), *JOB),
            (lambda: order.append("second"), *JOB),
        ):
            run_held_callbacks()

        assert order == ["first", "second"]

    @staticmethod
    def _taking(
        declared: int,
        received: List[Sequence[Any]],
    ) -> Any:
        """A callback declaring ``declared`` of DearPyGui's arguments, recording what it was handed."""
        recorders = (
            lambda: received.append(()),
            lambda sender: received.append((sender,)),
            lambda sender, app_data: received.append((sender, app_data)),
            lambda sender, app_data, user_data: received.append((sender, app_data, user_data)),
        )
        return recorders[declared]
