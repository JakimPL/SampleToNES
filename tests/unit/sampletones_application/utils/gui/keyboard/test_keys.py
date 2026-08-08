from dataclasses import dataclass

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.keys import (
    DIGIT_COUNT,
    FUNCTION_KEY_COUNT,
    FUNCTION_KEY_NAMES,
    FUNCTION_KEYS,
    HEX_KEYS,
    KEY_CODES,
    KEY_DISPLAY_NAMES,
    KEY_PAGE_DOWN,
    KEY_PAGE_UP,
    LETTER_COUNT,
    SIGN_KEYS,
    UNKNOWN_KEY,
    key_code,
    key_display,
)
from sampletones_shared.constants.symbols import HEXADECIMAL, MINUS, PLUS
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

UNNAMED_KEY = -1


class TestKeyDisplay(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        key: int
        expected: str

    test_cases = (
        TestCase(label="letter", key=dpg.mvKey_A, expected="A"),
        TestCase(label="last letter", key=dpg.mvKey_A + LETTER_COUNT - 1, expected="Z"),
        TestCase(label="digit", key=dpg.mvKey_0, expected="0"),
        TestCase(label="last digit", key=dpg.mvKey_0 + DIGIT_COUNT - 1, expected="9"),
        TestCase(label="first function key", key=dpg.mvKey_F1, expected="F1"),
        TestCase(
            label="last function key",
            key=dpg.mvKey_F1 + FUNCTION_KEY_COUNT - 1,
            expected="F12",
        ),
        TestCase(label="escape", key=dpg.mvKey_Escape, expected="Esc"),
        TestCase(label="page up", key=KEY_PAGE_UP, expected="PgUp"),
        TestCase(label="page down", key=KEY_PAGE_DOWN, expected="PgDn"),
        TestCase(label="plus", key=dpg.mvKey_Plus, expected=PLUS),
        TestCase(label="keypad plus", key=dpg.mvKey_Add, expected=f"Num{PLUS}"),
        TestCase(label="keypad minus", key=dpg.mvKey_Subtract, expected=f"Num{MINUS}"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_key_display(self, test_case: TestCase) -> None:
        assert key_display(test_case.key) == test_case.expected

    def test_a_key_the_table_omits_reads_as_a_placeholder(self) -> None:
        """A combination stays displayable whatever key a press carries."""
        assert key_display(UNNAMED_KEY) == UNKNOWN_KEY


class TestKeyCode(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        name: str
        expected: int

    test_cases = (
        TestCase(label="letter", name="A", expected=dpg.mvKey_A),
        TestCase(label="lower case letter", name="z", expected=dpg.mvKey_A + LETTER_COUNT - 1),
        TestCase(label="digit", name="7", expected=dpg.mvKey_0 + 7),
        TestCase(label="function key", name="F11", expected=dpg.mvKey_F1 + 10),
        TestCase(label="lower case function key", name="f11", expected=dpg.mvKey_F1 + 10),
        TestCase(label="page down", name="PgDn", expected=KEY_PAGE_DOWN),
        TestCase(label="upper case page down", name="PGDN", expected=KEY_PAGE_DOWN),
        TestCase(label="plus", name=PLUS, expected=dpg.mvKey_Plus),
        TestCase(label="keypad plus", name=f"Num{PLUS}", expected=dpg.mvKey_Add),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_key_code(self, test_case: TestCase) -> None:
        assert key_code(test_case.name) == test_case.expected

    def test_a_name_the_table_holds_no_key_under_raises(self) -> None:
        with pytest.raises(KeyError):
            key_code("Meta")


class TestKeyTable:
    def test_every_named_key_reads_back_as_itself(self) -> None:
        """A binding written down and read back arrives at the key it was written from."""
        assert all(key_code(name) == key for key, name in KEY_DISPLAY_NAMES.items())

    def test_each_key_carries_a_name_of_its_own(self) -> None:
        """Distinct names are what let a written combination name exactly one key."""
        assert len(KEY_CODES) == len(KEY_DISPLAY_NAMES)

    def test_the_page_keys_sit_among_the_keys_they_are_named_beside(self) -> None:
        """DearPyGui's page constants carry stale codes, so the live ones are named directly."""
        assert KEY_PAGE_DOWN == KEY_PAGE_UP + 1
        assert dpg.mvKey_Home == KEY_PAGE_DOWN + 1

    def test_the_function_keys_are_the_keys_the_function_names_carry(self) -> None:
        assert FUNCTION_KEYS == frozenset(FUNCTION_KEY_NAMES)


class TestCharacterKeys:
    def test_every_hexadecimal_digit_is_reachable(self) -> None:
        assert set(HEX_KEYS.values()) == set(HEXADECIMAL)

    def test_a_digit_key_enters_its_digit(self) -> None:
        assert HEX_KEYS[dpg.mvKey_0] == "0"

    def test_a_letter_key_enters_the_digit_it_stands_for(self) -> None:
        assert HEX_KEYS[dpg.mvKey_A + 5] == "F"

    def test_both_keys_of_a_sign_enter_it(self) -> None:
        """A keypad key enters the sign its main-row twin does."""
        assert SIGN_KEYS[dpg.mvKey_Add] == SIGN_KEYS[dpg.mvKey_Plus] == PLUS
        assert SIGN_KEYS[dpg.mvKey_Subtract] == SIGN_KEYS[dpg.mvKey_Minus] == MINUS
