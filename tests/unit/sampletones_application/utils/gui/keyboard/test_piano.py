from dataclasses import dataclass
from typing import Optional

import pytest

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.piano import semitone_of
from sampletones_shared.constants.music import OCTAVE_SEMITONES
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestSemitoneOf(BaseTestSuite):
    """A plain note key names its note, and the same key in a combination names none."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        press: str
        expected: Optional[int]

    test_cases = (
        TestCase(label="the C of the bottom row", press="Z", expected=0),
        TestCase(label="a black key above it", press="S", expected=1),
        TestCase(label="the C of the top row", press="Q", expected=OCTAVE_SEMITONES),
        TestCase(label="a digit on the top row", press="2", expected=OCTAVE_SEMITONES + 1),
        TestCase(label="a note key under shift", press="Shift+Z", expected=0),
        TestCase(label="undo", press="Ctrl+Z", expected=None),
        TestCase(label="save", press="Ctrl+S", expected=None),
        TestCase(label="a note key under alt", press="Alt+Z", expected=None),
        TestCase(label="undo on macOS", press="Super+Z", expected=None),
        TestCase(label="redo", press="Ctrl+Shift+Z", expected=None),
        TestCase(label="a key naming no note", press="K", expected=None),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_semitone_of(self, test_case: TestCase) -> None:
        assert semitone_of(_press(test_case.press)) == test_case.expected
