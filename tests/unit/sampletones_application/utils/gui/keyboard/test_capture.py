from dataclasses import dataclass
from typing import Final, List, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.capture import KeyCapture
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.keys import (
    KEY_MODIFIER_ALT,
    KEY_MODIFIER_CTRL,
    KEY_MODIFIER_SHIFT,
    KEY_MODIFIER_SUPER,
    KEY_RIGHT_SUPER,
)
from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL,
    CTRL_ALT,
    NO_MODIFIERS,
    SHIFT,
    SUPER,
    ModifierSet,
)
from sampletones_application.utils.gui.keyboard.router import KeyRouter
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ESCAPE: Final[KeyCombination] = KeyCombination(dpg.mvKey_Escape)
CANCEL: Final[Tuple[KeyCombination, ...]] = (ESCAPE,)


class Harness:
    """A capture over a router of its own, with the presses a reader makes spelled as methods."""

    def __init__(self) -> None:
        self.router = KeyRouter()
        self.captured: List[KeyCombination] = []
        self.cancelled = 0
        self.capture = KeyCapture(key_router=self.router, cancel=CANCEL)
        self.capture.on_captured = self.captured.append
        self.capture.on_cancelled = self._on_cancelled

    def press(self, key: int, modifiers: ModifierSet = NO_MODIFIERS) -> None:
        self.router.route(KeyEvent(key=key, modifiers=modifiers))

    def press_all(self, events: Tuple[KeyEvent, ...]) -> None:
        for event in events:
            self.press(event.key, event.modifiers)

    def _on_cancelled(self) -> None:
        self.cancelled += 1


@pytest.fixture(name="harness")
def harness_fixture() -> Harness:
    harness = Harness()
    harness.capture.start()
    return harness


class TestListening:
    def test_a_started_capture_holds_the_keyboard(self, harness: Harness) -> None:
        assert harness.capture.is_listening
        assert harness.router.is_modal_open

    def test_stopping_gives_the_keyboard_back(self, harness: Harness) -> None:
        harness.capture.stop()

        assert not harness.capture.is_listening
        assert not harness.router.is_modal_open

    def test_starting_twice_claims_the_keyboard_once(self, harness: Harness) -> None:
        harness.capture.start()
        harness.capture.stop()

        assert not harness.router.is_modal_open

    def test_stopping_twice_releases_the_claim_once(self, harness: Harness) -> None:
        """A second release would drop the claim of the dialog the capture sits above."""
        harness.router.push_modal(harness.capture)
        harness.capture.stop()
        harness.capture.stop()

        assert harness.router.is_modal_open


class TestCapturedPress(BaseTestSuite):
    """The combination a reader arrives at, spelled as the presses DearPyGui reports on the way.

    Holding a modifier reports it twice — under the key that carries it, and under the code ImGui
    reserves for the modifier — so a sequence states both, in the order they arrive.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        presses: Tuple[KeyEvent, ...]
        expected: Optional[KeyCombination]

    test_cases = (
        TestCase(
            label="a plain key",
            presses=(KeyEvent(key=dpg.mvKey_F5, modifiers=NO_MODIFIERS),),
            expected=KeyCombination(dpg.mvKey_F5),
        ),
        TestCase(
            label="control and a letter",
            presses=(
                KeyEvent(key=dpg.mvKey_LControl, modifiers=CTRL),
                KeyEvent(key=KEY_MODIFIER_CTRL, modifiers=CTRL),
                KeyEvent(key=dpg.mvKey_Z, modifiers=CTRL),
            ),
            expected=KeyCombination(dpg.mvKey_Z, CTRL),
        ),
        TestCase(
            label="alt and a navigation key",
            presses=(
                KeyEvent(key=dpg.mvKey_LAlt, modifiers=ALT),
                KeyEvent(key=KEY_MODIFIER_ALT, modifiers=ALT),
                KeyEvent(key=dpg.mvKey_Home, modifiers=ALT),
            ),
            expected=KeyCombination(dpg.mvKey_Home, ALT),
        ),
        TestCase(
            label="alt and an arrow key",
            presses=(
                KeyEvent(key=dpg.mvKey_LAlt, modifiers=ALT),
                KeyEvent(key=KEY_MODIFIER_ALT, modifiers=ALT),
                KeyEvent(key=dpg.mvKey_Up, modifiers=ALT),
            ),
            expected=KeyCombination(dpg.mvKey_Up, ALT),
        ),
        TestCase(
            label="two modifiers and a letter",
            presses=(
                KeyEvent(key=dpg.mvKey_LControl, modifiers=CTRL),
                KeyEvent(key=KEY_MODIFIER_CTRL, modifiers=CTRL),
                KeyEvent(key=dpg.mvKey_LAlt, modifiers=CTRL_ALT),
                KeyEvent(key=KEY_MODIFIER_ALT, modifiers=CTRL_ALT),
                KeyEvent(key=dpg.mvKey_G, modifiers=CTRL_ALT),
            ),
            expected=KeyCombination(dpg.mvKey_G, CTRL_ALT),
        ),
        TestCase(
            label="alt held on its own",
            presses=(
                KeyEvent(key=dpg.mvKey_LAlt, modifiers=ALT),
                KeyEvent(key=KEY_MODIFIER_ALT, modifiers=ALT),
            ),
            expected=None,
        ),
        TestCase(
            label="shift held on its own",
            presses=(
                KeyEvent(key=dpg.mvKey_RShift, modifiers=SHIFT),
                KeyEvent(key=KEY_MODIFIER_SHIFT, modifiers=SHIFT),
            ),
            expected=None,
        ),
        TestCase(
            label="super held on its own",
            presses=(
                KeyEvent(key=KEY_RIGHT_SUPER, modifiers=SUPER),
                KeyEvent(key=KEY_MODIFIER_SUPER, modifiers=SUPER),
            ),
            expected=None,
        ),
        TestCase(
            label="a key the table names none of",
            presses=(KeyEvent(key=dpg.mvKey_Browser_Back, modifiers=NO_MODIFIERS),),
            expected=None,
        ),
        TestCase(
            label="a modifier over a key the table names none of",
            presses=(
                KeyEvent(key=dpg.mvKey_LAlt, modifiers=ALT),
                KeyEvent(key=KEY_MODIFIER_ALT, modifiers=ALT),
                KeyEvent(key=dpg.mvKey_Browser_Forward, modifiers=ALT),
            ),
            expected=None,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_combination_a_sequence_of_presses_reports(
        self,
        test_case: TestCase,
        harness: Harness,
    ) -> None:
        harness.press_all(test_case.presses)

        assert harness.captured == ([] if test_case.expected is None else [test_case.expected])

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_capture_listens_on_until_a_combination_arrives(
        self,
        test_case: TestCase,
        harness: Harness,
    ) -> None:
        """A press that names nothing leaves the reader free to press again."""
        harness.press_all(test_case.presses)

        assert harness.capture.is_listening is (test_case.expected is None)
        assert harness.router.is_modal_open is (test_case.expected is None)

    @pytest.mark.parametrize(
        "test_case",
        [test_case for test_case in test_cases if test_case.expected is not None],
        ids=lambda test_case: test_case.label,
    )
    def test_a_reported_combination_is_one_a_binding_can_be_written_from(
        self,
        test_case: TestCase,
        harness: Harness,
    ) -> None:
        """What a capture reports is what an editor assigns, so it carries a written form."""
        harness.press_all(test_case.presses)

        assert all(combination.is_writable for combination in harness.captured)

    def test_a_key_pressed_after_one_the_table_names_none_of_is_read(self, harness: Harness) -> None:
        harness.press(dpg.mvKey_Browser_Back)
        harness.press(dpg.mvKey_D, CTRL)

        assert harness.captured == [KeyCombination(dpg.mvKey_D, CTRL)]


class TestCancelledCapture:
    def test_the_cancel_combination_ends_the_capture_without_assigning(self, harness: Harness) -> None:
        harness.press(dpg.mvKey_Escape)

        assert harness.captured == []
        assert harness.cancelled == 1
        assert not harness.capture.is_listening

    def test_the_cancel_key_under_a_modifier_is_a_combination_like_any_other(self, harness: Harness) -> None:
        harness.press(dpg.mvKey_Escape, CTRL)

        assert harness.captured == [KeyCombination(dpg.mvKey_Escape, CTRL)]
        assert harness.cancelled == 0
