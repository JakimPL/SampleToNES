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
    KEY_LEFT_SUPER,
    KEY_NAME_ALIASES,
    KEY_PAGE_DOWN,
    KEY_PAGE_UP,
    KEY_PLUS,
    KEY_QUOTE,
    KEY_RIGHT_SUPER,
    KEY_SEMICOLON,
    KEY_TILDE,
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

IMGUI_KEY_BLOCK_START = 512


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
            expected="F24",
        ),
        TestCase(label="escape", key=dpg.mvKey_Escape, expected="Esc"),
        TestCase(label="page up", key=KEY_PAGE_UP, expected="PgUp"),
        TestCase(label="page down", key=KEY_PAGE_DOWN, expected="PgDn"),
        TestCase(label="plus", key=KEY_PLUS, expected="Plus"),
        TestCase(label="minus", key=dpg.mvKey_Minus, expected="Minus"),
        TestCase(label="keypad plus", key=dpg.mvKey_Add, expected="NumPlus"),
        TestCase(label="keypad minus", key=dpg.mvKey_Subtract, expected="NumMinus"),
        TestCase(label="keypad digit", key=dpg.mvKey_NumPad0 + 5, expected="Num5"),
        TestCase(label="punctuation", key=dpg.mvKey_Comma, expected="Comma"),
        TestCase(label="quote", key=KEY_QUOTE, expected="Quote"),
        TestCase(label="semicolon", key=KEY_SEMICOLON, expected="Semicolon"),
        TestCase(label="tilde", key=KEY_TILDE, expected="Tilde"),
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
        TestCase(label="plus", name="Plus", expected=KEY_PLUS),
        TestCase(label="keypad plus", name="NumPlus", expected=dpg.mvKey_Add),
        TestCase(label="the plus glyph", name=PLUS, expected=KEY_PLUS),
        TestCase(label="the key the plus glyph shares", name="=", expected=KEY_PLUS),
        TestCase(label="the minus glyph", name=MINUS, expected=dpg.mvKey_Minus),
        TestCase(label="the keypad plus glyph", name=f"Num{PLUS}", expected=dpg.mvKey_Add),
        TestCase(label="a spelling from the key constant", name="Add", expected=dpg.mvKey_Add),
        TestCase(label="a written page name", name="PageUp", expected=KEY_PAGE_UP),
        TestCase(label="a written escape", name="escape", expected=dpg.mvKey_Escape),
        TestCase(label="a punctuation glyph", name="/", expected=dpg.mvKey_Slash),
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
            key_code("Nonesuch")


class TestKeyTable:
    def test_every_named_key_reads_back_as_itself(self) -> None:
        """A binding written down and read back arrives at the key it was written from."""
        assert all(key_code(name) == key for key, name in KEY_DISPLAY_NAMES.items())

    def test_each_key_carries_a_name_of_its_own(self) -> None:
        """Distinct names are what let a written combination name exactly one key."""
        assert len(set(KEY_DISPLAY_NAMES.values())) == len(KEY_DISPLAY_NAMES)

    def test_every_accepted_spelling_reaches_a_named_key(self) -> None:
        assert all(alias.casefold() in KEY_CODES for alias in KEY_NAME_ALIASES)

    def test_a_spelling_reaches_the_key_it_names(self) -> None:
        assert all(key_display(key_code(alias)) == name for alias, name in KEY_NAME_ALIASES.items())

    def test_every_key_sits_in_the_block_a_press_reports_from(self) -> None:
        """A press reports an ImGuiKey, so every key the table names carries a code from that
        block."""
        assert all(key >= IMGUI_KEY_BLOCK_START for key in KEY_DISPLAY_NAMES)

    def test_the_function_keys_are_the_keys_the_function_names_carry(self) -> None:
        assert FUNCTION_KEYS == frozenset(FUNCTION_KEY_NAMES)


class TestWrittenKeys(BaseTestSuite):
    """The codes written out in the table are the ones a press carries, each seated between the two
    keys DearPyGui names on either side of it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        preceding: int
        key: int
        following: int

    test_cases = (
        TestCase(label="page up", preceding=dpg.mvKey_Down, key=KEY_PAGE_UP, following=KEY_PAGE_DOWN),
        TestCase(label="page down", preceding=KEY_PAGE_UP, key=KEY_PAGE_DOWN, following=dpg.mvKey_Home),
        TestCase(
            label="left super",
            preceding=dpg.mvKey_LAlt,
            key=KEY_LEFT_SUPER,
            following=dpg.mvKey_RControl,
        ),
        TestCase(
            label="right super",
            preceding=dpg.mvKey_RAlt,
            key=KEY_RIGHT_SUPER,
            following=dpg.mvKey_Menu,
        ),
        TestCase(
            label="quote",
            preceding=dpg.mvKey_F1 + FUNCTION_KEY_COUNT - 1,
            key=KEY_QUOTE,
            following=dpg.mvKey_Comma,
        ),
        TestCase(label="semicolon", preceding=dpg.mvKey_Slash, key=KEY_SEMICOLON, following=KEY_PLUS),
        TestCase(label="plus", preceding=KEY_SEMICOLON, key=KEY_PLUS, following=dpg.mvKey_Open_Brace),
        TestCase(
            label="tilde",
            preceding=dpg.mvKey_Close_Brace,
            key=KEY_TILDE,
            following=dpg.mvKey_CapsLock,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_written_key_seats_between_the_keys_it_neighbours(self, test_case: TestCase) -> None:
        assert test_case.key == test_case.preceding + 1
        assert test_case.following == test_case.key + 1


class TestCharacterKeys:
    def test_every_hexadecimal_digit_is_reachable(self) -> None:
        assert set(HEX_KEYS.values()) == set(HEXADECIMAL)

    def test_a_digit_key_enters_its_digit(self) -> None:
        assert HEX_KEYS[dpg.mvKey_0] == "0"

    def test_a_letter_key_enters_the_digit_it_stands_for(self) -> None:
        assert HEX_KEYS[dpg.mvKey_A + 5] == "F"

    def test_both_keys_of_a_sign_enter_it(self) -> None:
        """A keypad key enters the sign its main-row twin does."""
        assert SIGN_KEYS[dpg.mvKey_Add] == SIGN_KEYS[KEY_PLUS] == PLUS
        assert SIGN_KEYS[dpg.mvKey_Subtract] == SIGN_KEYS[dpg.mvKey_Minus] == MINUS
