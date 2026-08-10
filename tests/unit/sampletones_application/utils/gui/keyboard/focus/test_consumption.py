from dataclasses import dataclass

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.focus.consumption import (
    field_consumes_key,
)
from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    ModifierSet,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


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
            label="text field yields Alt+F4",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_F4,
            modifiers=ALT,
            expected=False,
        ),
        TestCase(
            label="text field yields F11",
            kind=FieldKind.TEXT_ENTRY,
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
