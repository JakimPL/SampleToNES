from dataclasses import dataclass
from typing import Final

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.focus.consumption import (
    field_consumes_key,
)
from sampletones_application.utils.gui.keyboard.focus.items import field_kind
from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL,
    CTRL_ALT,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    SUPER,
    SUPER_SHIFT,
    Modifier,
    ModifierSet,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_application.utils.gui.keyboard.focus.item_tree import INPUT_INT, SLIDER_INT

ALT_SHIFT: Final[ModifierSet] = frozenset({Modifier.ALT, Modifier.SHIFT})
SUPER_ALT: Final[ModifierSet] = frozenset({Modifier.SUPER, Modifier.ALT})


class TestFieldConsumesKey(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        kind: FieldKind
        key: int
        modifiers: ModifierSet = NO_MODIFIERS
        expected: bool

    test_cases = (
        TestCase(
            label="no field lets every key through",
            kind=FieldKind.NONE,
            key=dpg.mvKey_Spacebar,
            expected=False,
        ),
        TestCase(
            label="text field types a space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            expected=True,
        ),
        TestCase(
            label="text field types a shifted space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            modifiers=SHIFT,
            expected=True,
        ),
        TestCase(
            label="text field yields Ctrl+Space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            modifiers=CTRL,
            expected=False,
        ),
        TestCase(
            label="text field yields Ctrl+Shift+Space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            modifiers=CTRL_SHIFT,
            expected=False,
        ),
        TestCase(
            label="text field cancels on Escape",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Escape,
            expected=True,
        ),
        TestCase(
            label="text field commits on Enter",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Return,
            expected=True,
        ),
        TestCase(
            label="text field selects all on Ctrl+A",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_A,
            modifiers=CTRL,
            expected=True,
        ),
        TestCase(
            label="text field undoes on Ctrl+Z",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Z,
            modifiers=CTRL,
            expected=True,
        ),
        TestCase(
            label="text field redoes on Ctrl+Shift+Z",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Z,
            modifiers=CTRL_SHIFT,
            expected=True,
        ),
        TestCase(
            label="text field yields Ctrl+Shift+A",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_A,
            modifiers=CTRL_SHIFT,
            expected=False,
        ),
        TestCase(
            label="text field yields Ctrl+S",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_S,
            modifiers=CTRL,
            expected=False,
        ),
        TestCase(
            label="text field yields Alt on a function key, so Alt+F4 exits",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_F4,
            modifiers=ALT,
            expected=False,
        ),
        TestCase(
            label="text field yields Alt on a caret key, Alt+Up",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Up,
            modifiers=ALT,
            expected=False,
        ),
        TestCase(
            label="text field yields Alt on an editing key, Alt+Home",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Home,
            modifiers=ALT,
            expected=False,
        ),
        TestCase(
            label="text field types AltGr on a digit, which Linux reports as Alt+2",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_2,
            modifiers=ALT,
            expected=True,
        ),
        TestCase(
            label="text field types AltGr on a letter, which Linux reports as Alt+E",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_E,
            modifiers=ALT,
            expected=True,
        ),
        TestCase(
            label="text field types a shifted AltGr letter, Alt+Shift+S",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_S,
            modifiers=ALT_SHIFT,
            expected=True,
        ),
        TestCase(
            label="text field types AltGr on punctuation, Alt+Period",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Period,
            modifiers=ALT,
            expected=True,
        ),
        TestCase(
            label="text field types AltGr on a letter, which Windows reports as Ctrl+Alt+S",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_S,
            modifiers=CTRL_ALT,
            expected=True,
        ),
        TestCase(
            label="text field yields Ctrl+Alt on a caret key",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Left,
            modifiers=CTRL_ALT,
            expected=False,
        ),
        TestCase(
            label="text field yields Super+S, so Cmd+S saves from a field",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_S,
            modifiers=SUPER,
            expected=False,
        ),
        TestCase(
            label="text field yields Super+Space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            modifiers=SUPER,
            expected=False,
        ),
        TestCase(
            label="text field yields Super+Alt+S, so Cmd+Option+S saves from a field",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_S,
            modifiers=SUPER_ALT,
            expected=False,
        ),
        TestCase(
            label="text field yields Super+Shift+A",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_A,
            modifiers=SUPER_SHIFT,
            expected=False,
        ),
        TestCase(
            label="text field copies on Super+C",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_C,
            modifiers=SUPER,
            expected=True,
        ),
        TestCase(
            label="text field pastes on Super+V",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_V,
            modifiers=SUPER,
            expected=True,
        ),
        TestCase(
            label="text field undoes on Super+Z",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Z,
            modifiers=SUPER,
            expected=True,
        ),
        TestCase(
            label="text field redoes on Super+Shift+Z",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Z,
            modifiers=SUPER_SHIFT,
            expected=True,
        ),
        TestCase(
            label="text field yields F11",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_F11,
            expected=False,
        ),
        TestCase(
            label="number field types a digit",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_2,
            expected=True,
        ),
        TestCase(
            label="number field types a minus sign",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_Minus,
            expected=True,
        ),
        TestCase(
            label="number field commits on Enter",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_Return,
            expected=True,
        ),
        TestCase(
            label="number field selects all on Ctrl+A",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_A,
            modifiers=CTRL,
            expected=True,
        ),
        TestCase(
            label="number field pastes on Super+V",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_V,
            modifiers=SUPER,
            expected=True,
        ),
        TestCase(
            label="number field yields Ctrl+S",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_S,
            modifiers=CTRL,
            expected=False,
        ),
        TestCase(
            label="number field yields Ctrl+Alt+S, which types nothing in a number",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_S,
            modifiers=CTRL_ALT,
            expected=False,
        ),
        TestCase(
            label="number field yields Alt+2, which types nothing in a number",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_2,
            modifiers=ALT,
            expected=False,
        ),
        TestCase(
            label="number field yields F11",
            kind=FieldKind.NUMBER_ENTRY,
            key=dpg.mvKey_F11,
            expected=False,
        ),
        TestCase(
            label="open combo yields a plain space",
            kind=FieldKind.CHOICE,
            key=dpg.mvKey_Spacebar,
            expected=False,
        ),
        TestCase(
            label="open combo closes on Escape",
            kind=FieldKind.CHOICE,
            key=dpg.mvKey_Escape,
            expected=True,
        ),
        TestCase(
            label="open combo yields Ctrl+A",
            kind=FieldKind.CHOICE,
            key=dpg.mvKey_A,
            modifiers=CTRL,
            expected=False,
        ),
        TestCase(
            label="open combo yields Alt+2",
            kind=FieldKind.CHOICE,
            key=dpg.mvKey_2,
            modifiers=ALT,
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_field_consumes_key(self, test_case: TestCase) -> None:
        consumed = field_consumes_key(
            test_case.kind,
            test_case.key,
            test_case.modifiers,
        )

        assert consumed is test_case.expected


class TestChordsFollowTheirModifiers:
    def test_a_ctrl_chord_letter_reaches_the_shortcut_when_shift_joins_it(self) -> None:
        """Ctrl+Shift+A is an application shortcut, so a text field yields it while keeping Ctrl+A.

        The chord table is keyed by the exact modifier set, which keeps the field to the chords its
        modifiers actually name.
        """
        assert field_consumes_key(FieldKind.TEXT_ENTRY, dpg.mvKey_A, CTRL) is True
        assert field_consumes_key(FieldKind.TEXT_ENTRY, dpg.mvKey_A, CTRL_SHIFT) is False

    def test_redo_stays_with_the_field_as_a_ctrl_shift_chord(self) -> None:
        assert field_consumes_key(FieldKind.TEXT_ENTRY, dpg.mvKey_Z, CTRL_SHIFT) is True


class TestANumberFieldYieldsAltChords(BaseTestSuite):
    """A number field types no character with AltGr or Option, so an Alt chord pressed in one reaches
    its shortcut."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        item_type: str
        modifiers: ModifierSet

    test_cases = (
        TestCase(label="Ctrl+Alt+S from an integer input", item_type=INPUT_INT, modifiers=CTRL_ALT),
        TestCase(label="Alt+S from a slider", item_type=SLIDER_INT, modifiers=ALT),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_chord_reaches_its_shortcut(self, test_case: TestCase) -> None:
        assert field_consumes_key(field_kind(test_case.item_type), dpg.mvKey_S, test_case.modifiers) is False
