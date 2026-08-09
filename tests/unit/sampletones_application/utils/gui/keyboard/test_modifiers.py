import platform
from dataclasses import dataclass
from typing import List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.keys import (
    KEY_LEFT_SUPER,
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
    CTRL_ALT_SHIFT,
    CTRL_SHIFT,
    MODIFIER_NAMES,
    NO_MODIFIERS,
    RESERVED_MODIFIER_KEYS,
    SHIFT,
    SUPER,
    Modifier,
    ModifierSet,
    capture_modifiers,
    is_modifier_key,
    modifier_display,
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
L_SUPER = KEY_LEFT_SUPER
R_SUPER = KEY_RIGHT_SUPER


def _hold(monkeypatch: pytest.MonkeyPatch, held: List[int]) -> None:
    """Reports ``held`` as the keys DearPyGui sees down."""
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
        TestCase(label="left super", held=[L_SUPER], expected=SUPER),
        TestCase(label="right super", held=[R_SUPER], expected=SUPER),
        TestCase(label="control and shift", held=[L_CONTROL, R_SHIFT], expected=CTRL_SHIFT),
        TestCase(label="control and alt", held=[R_CONTROL, L_ALT], expected=CTRL_ALT),
        TestCase(
            label="control, alt and shift",
            held=[L_CONTROL, L_SHIFT, L_ALT],
            expected=CTRL_ALT_SHIFT,
        ),
        TestCase(
            label="every modifier",
            held=[L_CONTROL, L_SHIFT, L_ALT, L_SUPER],
            expected=frozenset(Modifier),
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


class TestModifierKeys(BaseTestSuite):
    """A modifier reaches a handler twice, under its own key and under the code reserved for it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        key: int
        expected: bool

    test_cases = (
        TestCase(label="left control", key=L_CONTROL, expected=True),
        TestCase(label="right control", key=R_CONTROL, expected=True),
        TestCase(label="left shift", key=L_SHIFT, expected=True),
        TestCase(label="right shift", key=R_SHIFT, expected=True),
        TestCase(label="left alt", key=L_ALT, expected=True),
        TestCase(label="right alt", key=R_ALT, expected=True),
        TestCase(label="left super", key=L_SUPER, expected=True),
        TestCase(label="right super", key=R_SUPER, expected=True),
        TestCase(label="the code reserved for control", key=KEY_MODIFIER_CTRL, expected=True),
        TestCase(label="the code reserved for shift", key=KEY_MODIFIER_SHIFT, expected=True),
        TestCase(label="the code reserved for alt", key=KEY_MODIFIER_ALT, expected=True),
        TestCase(label="the code reserved for super", key=KEY_MODIFIER_SUPER, expected=True),
        TestCase(label="a letter", key=dpg.mvKey_G, expected=False),
        TestCase(label="a navigation key", key=dpg.mvKey_Home, expected=False),
        TestCase(label="the menu key", key=dpg.mvKey_Menu, expected=False),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_is_modifier_key(self, test_case: TestCase) -> None:
        assert is_modifier_key(test_case.key) is test_case.expected

    def test_every_modifier_carries_a_code_of_its_own(self) -> None:
        assert set(RESERVED_MODIFIER_KEYS) == set(Modifier)


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
            label="control, alt and shift",
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

    def test_the_super_key_leads_the_combination_it_is_part_of(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Linux")

        assert modifiers_display(frozenset({Modifier.SHIFT, Modifier.SUPER})) == (
            "Super",
            "Shift",
        )


class TestSuperName(BaseTestSuite):
    """One key wears three names, so a combination reads the way the keyboard is labelled."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: str
        expected: str

    test_cases = (
        TestCase(label="linux", system="Linux", expected="Super"),
        TestCase(label="windows", system="Windows", expected="Win"),
        TestCase(label="macos", system="Darwin", expected="Cmd"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_super_key_reads_as_the_platform_labels_it(
        self,
        test_case: TestCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform, "system", lambda: test_case.system)

        assert modifier_display(Modifier.SUPER) == test_case.expected

    def test_every_other_modifier_reads_the_same_everywhere(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform, "system", lambda: "Darwin")

        assert modifier_display(Modifier.CTRL) == "Ctrl"


class TestModifierNames(BaseTestSuite):
    """Every spelling is readable on every platform, which lets one platform's scheme be read on
    another."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        name: str
        expected: Modifier

    test_cases = (
        TestCase(label="ctrl", name="ctrl", expected=Modifier.CTRL),
        TestCase(label="control", name="control", expected=Modifier.CTRL),
        TestCase(label="alt", name="alt", expected=Modifier.ALT),
        TestCase(label="option", name="option", expected=Modifier.ALT),
        TestCase(label="shift", name="shift", expected=Modifier.SHIFT),
        TestCase(label="super", name="super", expected=Modifier.SUPER),
        TestCase(label="cmd", name="cmd", expected=Modifier.SUPER),
        TestCase(label="command", name="command", expected=Modifier.SUPER),
        TestCase(label="win", name="win", expected=Modifier.SUPER),
        TestCase(label="meta", name="meta", expected=Modifier.SUPER),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_spelling_names_its_modifier(self, test_case: TestCase) -> None:
        assert MODIFIER_NAMES[test_case.name] == test_case.expected

    def test_every_modifier_answers_to_the_name_it_displays_under(self) -> None:
        assert all(modifier.value.casefold() in MODIFIER_NAMES for modifier in Modifier)
