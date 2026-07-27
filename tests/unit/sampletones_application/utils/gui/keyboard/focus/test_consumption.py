from dataclasses import dataclass

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.focus.consumption import field_consumes_key
from sampletones_application.utils.gui.keyboard.focus.kind import FieldKind
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestFieldConsumesKey(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        kind: FieldKind
        key: int
        ctrl: bool = False
        shift: bool = False
        alt: bool = False
        expected: bool

    test_cases = [
        TestCase(
            label="no field lets every key through",
            kind=FieldKind.NONE,
            key=dpg.mvKey_Spacebar,
            expected=False,
        ),
        TestCase(label="text field types a space", kind=FieldKind.TEXT_ENTRY, key=dpg.mvKey_Spacebar, expected=True),
        TestCase(
            label="text field types a shifted space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            shift=True,
            expected=True,
        ),
        TestCase(
            label="text field yields Ctrl+Space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            ctrl=True,
            expected=False,
        ),
        TestCase(
            label="text field yields Ctrl+Shift+Space",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Spacebar,
            ctrl=True,
            shift=True,
            expected=False,
        ),
        TestCase(label="text field cancels on Escape", kind=FieldKind.TEXT_ENTRY, key=dpg.mvKey_Escape, expected=True),
        TestCase(label="text field commits on Enter", kind=FieldKind.TEXT_ENTRY, key=dpg.mvKey_Return, expected=True),
        TestCase(
            label="text field selects all on Ctrl+A",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_A,
            ctrl=True,
            expected=True,
        ),
        TestCase(
            label="text field undoes on Ctrl+Z",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Z,
            ctrl=True,
            expected=True,
        ),
        TestCase(
            label="text field redoes on Ctrl+Shift+Z",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_Z,
            ctrl=True,
            shift=True,
            expected=True,
        ),
        TestCase(
            label="text field yields Ctrl+S",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_S,
            ctrl=True,
            expected=False,
        ),
        TestCase(
            label="text field yields Alt+F4",
            kind=FieldKind.TEXT_ENTRY,
            key=dpg.mvKey_F4,
            alt=True,
            expected=False,
        ),
        TestCase(label="text field yields F11", kind=FieldKind.TEXT_ENTRY, key=dpg.mvKey_F11, expected=False),
        TestCase(
            label="open combo yields a plain space",
            kind=FieldKind.CHOICE,
            key=dpg.mvKey_Spacebar,
            expected=False,
        ),
        TestCase(label="open combo closes on Escape", kind=FieldKind.CHOICE, key=dpg.mvKey_Escape, expected=True),
        TestCase(label="open combo yields Ctrl+A", kind=FieldKind.CHOICE, key=dpg.mvKey_A, ctrl=True, expected=False),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_field_consumes_key(self, test_case: TestCase) -> None:
        consumed = field_consumes_key(
            test_case.kind,
            test_case.key,
            ctrl=test_case.ctrl,
            shift=test_case.shift,
            alt=test_case.alt,
        )

        assert consumed is test_case.expected
