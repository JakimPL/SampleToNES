from dataclasses import dataclass
from unittest.mock import patch

import pytest

from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    SUPER,
    ModifierSet,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

MODULE = "sampletones_application.utils.gui.keyboard.event"

KEY = 65


def test_capture_carries_the_key_and_the_modifiers_held_with_it() -> None:
    with patch(f"{MODULE}.capture_modifiers", lambda: CTRL_SHIFT):
        event = KeyEvent.capture(KEY)

    assert event == KeyEvent(key=KEY, modifiers=CTRL_SHIFT)


class TestIsPlain(BaseTestSuite):
    """A press types its key alone or under Shift, and Ctrl, Alt or Super make it a command."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        modifiers: ModifierSet
        expected: bool

    test_cases = (
        TestCase(label="no modifier", modifiers=NO_MODIFIERS, expected=True),
        TestCase(label="shift, as a capital is typed", modifiers=SHIFT, expected=True),
        TestCase(label="ctrl", modifiers=CTRL, expected=False),
        TestCase(label="alt", modifiers=ALT, expected=False),
        TestCase(label="super, the command key on macOS", modifiers=SUPER, expected=False),
        TestCase(label="ctrl with shift", modifiers=CTRL_SHIFT, expected=False),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_is_plain(self, test_case: TestCase) -> None:
        assert KeyEvent(key=KEY, modifiers=test_case.modifiers).is_plain is test_case.expected
