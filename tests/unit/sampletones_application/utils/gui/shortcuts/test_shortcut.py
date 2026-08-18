from dataclasses import dataclass
from typing import Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import (
    CTRL,
    CTRL_SHIFT,
    NO_MODIFIERS,
)
from sampletones_application.utils.gui.shortcuts.shortcut import NO_COMBINATION, Shortcut
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

REDO = KeyCombination(dpg.mvKey_Y, CTRL)
REDO_ALIAS = KeyCombination(dpg.mvKey_Z, CTRL_SHIFT)
INSERT = KeyCombination(dpg.mvKey_Plus)
INSERT_ALIAS = KeyCombination(dpg.mvKey_Add)


class TestCombinations(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut: Shortcut
        expected: Tuple[KeyCombination, ...]

    test_cases = (
        TestCase(
            label="a combination of its own",
            shortcut=Shortcut(combination=REDO),
            expected=(REDO,),
        ),
        TestCase(
            label="the displayed combination ahead of its aliases",
            shortcut=Shortcut(combination=REDO, aliases=(REDO_ALIAS,)),
            expected=(REDO, REDO_ALIAS),
        ),
        TestCase(
            label="aliases while no combination is assigned",
            shortcut=Shortcut(combination=None, aliases=(INSERT_ALIAS,)),
            expected=(INSERT_ALIAS,),
        ),
        TestCase(
            label="no combination at all",
            shortcut=Shortcut(combination=None),
            expected=(),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_combinations(self, test_case: TestCase) -> None:
        assert test_case.shortcut.combinations() == test_case.expected


class TestMatches(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut: Shortcut
        event: KeyEvent
        expected: bool

    test_cases = (
        TestCase(
            label="the displayed combination",
            shortcut=Shortcut(combination=REDO, aliases=(REDO_ALIAS,)),
            event=KeyEvent(key=dpg.mvKey_Y, modifiers=CTRL),
            expected=True,
        ),
        TestCase(
            label="an alias",
            shortcut=Shortcut(combination=REDO, aliases=(REDO_ALIAS,)),
            event=KeyEvent(key=dpg.mvKey_Z, modifiers=CTRL_SHIFT),
            expected=True,
        ),
        TestCase(
            label="a combination bound elsewhere",
            shortcut=Shortcut(combination=REDO, aliases=(REDO_ALIAS,)),
            event=KeyEvent(key=dpg.mvKey_Z, modifiers=CTRL),
            expected=False,
        ),
        TestCase(
            label="an alias while no combination is assigned",
            shortcut=Shortcut(combination=None, aliases=(INSERT_ALIAS,)),
            event=KeyEvent(key=dpg.mvKey_Add, modifiers=NO_MODIFIERS),
            expected=True,
        ),
        TestCase(
            label="any press while the action carries no combination",
            shortcut=Shortcut(combination=None),
            event=KeyEvent(key=dpg.mvKey_Y, modifiers=CTRL),
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_matches(self, test_case: TestCase) -> None:
        assert test_case.shortcut.matches(test_case.event) is test_case.expected


class TestDisplay:
    def test_an_action_reads_under_the_combination_it_displays(self) -> None:
        assert Shortcut(combination=REDO, aliases=(REDO_ALIAS,)).display() == "Ctrl+Y"

    def test_an_action_carrying_no_combination_reads_empty(self) -> None:
        """A menu lists an action whether or not a combination is assigned to it."""
        assert Shortcut(combination=None).display() == NO_COMBINATION


class TestBinding:
    def test_an_action_stays_behind_field_focus_unless_it_is_declared_transparent(
        self,
    ) -> None:
        assert Shortcut(combination=INSERT).field_transparent is False

    def test_a_transparent_action_carries_the_declaration(self) -> None:
        assert Shortcut(combination=INSERT, field_transparent=True).field_transparent is True
