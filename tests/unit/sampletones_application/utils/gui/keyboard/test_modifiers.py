from dataclasses import dataclass
from typing import List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL,
    CTRL_ALT,
    CTRL_ALT_SHIFT,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    Modifier,
    ModifierSet,
    capture_modifiers,
    modifiers_display,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

L_CONTROL = dpg.mvKey_LControl
R_CONTROL = dpg.mvKey_RControl
L_SHIFT = dpg.mvKey_LShift
R_SHIFT = dpg.mvKey_RShift
L_ALT = dpg.mvKey_LAlt
R_ALT = dpg.mvKey_RAlt


def _hold(monkeypatch: pytest.MonkeyPatch, held: List[int]) -> None:
    """Reports ``held`` as the keys DearPyGui sees down, leaving its key codes as they are."""
    monkeypatch.setattr(dpg, "is_key_down", lambda key: key in held)


class TestCaptureModifiers(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        held: List[int]
        expected: ModifierSet

    test_cases = (
        TestCase(label="no modifier held", held=[], expected=NO_MODIFIERS),
        TestCase(label="left control", held=[L_CONTROL], expected=CTRL),
        TestCase(label="right control", held=[R_CONTROL], expected=CTRL),
        TestCase(label="left shift", held=[L_SHIFT], expected=SHIFT),
        TestCase(label="right shift", held=[R_SHIFT], expected=SHIFT),
        TestCase(label="left alt", held=[L_ALT], expected=ALT),
        TestCase(label="right alt", held=[R_ALT], expected=ALT),
        TestCase(label="control and shift", held=[L_CONTROL, R_SHIFT], expected=CTRL_SHIFT),
        TestCase(label="control and alt", held=[R_CONTROL, L_ALT], expected=CTRL_ALT),
        TestCase(
            label="every modifier",
            held=[L_CONTROL, L_SHIFT, L_ALT],
            expected=CTRL_ALT_SHIFT,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_capture_modifiers(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _hold(monkeypatch, test_case.held)

        assert capture_modifiers() == test_case.expected

    def test_both_keys_of_one_modifier_report_it_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _hold(monkeypatch, [L_CONTROL, R_CONTROL])

        assert capture_modifiers() == CTRL


class TestModifiersDisplay(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        modifiers: ModifierSet
        expected: Tuple[str, ...]

    test_cases = (
        TestCase(label="no modifier", modifiers=NO_MODIFIERS, expected=()),
        TestCase(label="control", modifiers=CTRL, expected=("Ctrl",)),
        TestCase(label="shift", modifiers=SHIFT, expected=("Shift",)),
        TestCase(label="alt", modifiers=ALT, expected=("Alt",)),
        TestCase(label="control and shift", modifiers=CTRL_SHIFT, expected=("Ctrl", "Shift")),
        TestCase(label="control and alt", modifiers=CTRL_ALT, expected=("Ctrl", "Alt")),
        TestCase(
            label="every modifier",
            modifiers=CTRL_ALT_SHIFT,
            expected=("Ctrl", "Alt", "Shift"),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_modifiers_display(self, test_case: TestCase) -> None:
        assert modifiers_display(test_case.modifiers) == test_case.expected

    def test_the_order_a_caller_names_its_modifiers_leaves_the_display_unchanged(
        self,
    ) -> None:
        """One combination reads the same wherever it is shown, whatever order it was declared in."""
        assert modifiers_display(frozenset({Modifier.SHIFT, Modifier.CTRL})) == (
            "Ctrl",
            "Shift",
        )
