from dataclasses import dataclass
from typing import Final, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.combination import (
    KEY_LIST_JOINER,
    KeyCombination,
    display_combinations,
    parse_combinations,
)
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.keys import (
    KEY_MODIFIER_ALT,
    KEY_PAGE_DOWN,
    KEY_PLUS,
)
from sampletones_application.utils.gui.keyboard.modifiers import (
    ALT,
    CTRL,
    CTRL_ALT_SHIFT,
    CTRL_SHIFT,
    NO_MODIFIERS,
    SHIFT,
    ModifierSet,
)
from sampletones_shared.constants.symbols import PLUS
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

CTRL_COMMA: Final[KeyCombination] = KeyCombination(dpg.mvKey_Comma, CTRL)
CTRL_Y: Final[KeyCombination] = KeyCombination(dpg.mvKey_Y, CTRL)
CTRL_SHIFT_Z: Final[KeyCombination] = KeyCombination(dpg.mvKey_Z, CTRL_SHIFT)
COMMA: Final[KeyCombination] = KeyCombination(dpg.mvKey_Comma)
CTRL_PLUS: Final[KeyCombination] = KeyCombination(KEY_PLUS, CTRL)

WRITTEN_COMBINATIONS = (
    "Ctrl+Shift+Z",
    "Ctrl+D",
    "F11",
    "Ctrl+PgDn",
    "Alt+Home",
    "Shift+Del",
    "Ctrl+Ins",
    "Plus",
    "Ctrl+Plus",
    "NumPlus",
    "Ctrl+Alt+Shift+Space",
)


class TestMatches(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        combination: KeyCombination
        event: KeyEvent
        expected: bool

    test_cases = (
        TestCase(
            label="the key under the modifiers it names",
            combination=KeyCombination(dpg.mvKey_D, CTRL),
            event=KeyEvent(key=dpg.mvKey_D, modifiers=CTRL),
            expected=True,
        ),
        TestCase(
            label="a plain key under no modifier",
            combination=KeyCombination(dpg.mvKey_F1),
            event=KeyEvent(key=dpg.mvKey_F1, modifiers=NO_MODIFIERS),
            expected=True,
        ),
        TestCase(
            label="another key under the same modifiers",
            combination=KeyCombination(dpg.mvKey_D, CTRL),
            event=KeyEvent(key=dpg.mvKey_E, modifiers=CTRL),
            expected=False,
        ),
        TestCase(
            label="the key under no modifier",
            combination=KeyCombination(dpg.mvKey_D, CTRL),
            event=KeyEvent(key=dpg.mvKey_D, modifiers=NO_MODIFIERS),
            expected=False,
        ),
        TestCase(
            label="the key under a further modifier",
            combination=KeyCombination(dpg.mvKey_D, CTRL),
            event=KeyEvent(key=dpg.mvKey_D, modifiers=CTRL_SHIFT),
            expected=False,
        ),
        TestCase(
            label="a plain key under a modifier",
            combination=KeyCombination(dpg.mvKey_F1),
            event=KeyEvent(key=dpg.mvKey_F1, modifiers=SHIFT),
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_matches(self, test_case: TestCase) -> None:
        assert test_case.combination.matches(test_case.event) is test_case.expected


class TestDisplay(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        key: int
        modifiers: ModifierSet
        expected: str

    test_cases = (
        TestCase(label="a plain key", key=dpg.mvKey_F1, modifiers=NO_MODIFIERS, expected="F1"),
        TestCase(label="one modifier", key=dpg.mvKey_D, modifiers=CTRL, expected="Ctrl+D"),
        TestCase(
            label="two modifiers in canonical order",
            key=dpg.mvKey_Z,
            modifiers=CTRL_SHIFT,
            expected="Ctrl+Shift+Z",
        ),
        TestCase(
            label="control, alt and shift",
            key=dpg.mvKey_Spacebar,
            modifiers=CTRL_ALT_SHIFT,
            expected="Ctrl+Alt+Shift+Space",
        ),
        TestCase(label="a page key", key=KEY_PAGE_DOWN, modifiers=CTRL, expected="Ctrl+PgDn"),
        TestCase(label="the key the separator glyph sits on", key=KEY_PLUS, modifiers=CTRL, expected="Ctrl+Plus"),
        TestCase(label="a navigation key", key=dpg.mvKey_Home, modifiers=ALT, expected="Alt+Home"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_display(self, test_case: TestCase) -> None:
        assert KeyCombination(test_case.key, test_case.modifiers).display() == test_case.expected


class TestWritable(BaseTestSuite):
    """A combination is storable once its key carries a name, which a press alone does not promise."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        key: int
        modifiers: ModifierSet
        expected: bool

    test_cases = (
        TestCase(label="a letter", key=dpg.mvKey_D, modifiers=CTRL, expected=True),
        TestCase(label="a navigation key", key=dpg.mvKey_Home, modifiers=ALT, expected=True),
        TestCase(label="a written key", key=KEY_PAGE_DOWN, modifiers=NO_MODIFIERS, expected=True),
        TestCase(
            label="the code reserved for alt",
            key=KEY_MODIFIER_ALT,
            modifiers=ALT,
            expected=False,
        ),
        TestCase(
            label="a key the table names none of",
            key=dpg.mvKey_Browser_Back,
            modifiers=NO_MODIFIERS,
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_is_writable(self, test_case: TestCase) -> None:
        assert KeyCombination(test_case.key, test_case.modifiers).is_writable is test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        [test_case for test_case in test_cases if test_case.expected],
        ids=lambda test_case: test_case.label,
    )
    def test_a_writable_combination_reads_back_as_itself(self, test_case: TestCase) -> None:
        combination = KeyCombination(test_case.key, test_case.modifiers)

        assert KeyCombination.parse(combination.display()) == combination

    @pytest.mark.parametrize(
        "test_case",
        [test_case for test_case in test_cases if not test_case.expected],
        ids=lambda test_case: test_case.label,
    )
    def test_the_rest_are_shown_and_left_at_that(self, test_case: TestCase) -> None:
        """A combination stays displayable whatever a press carries, and stops short of storable."""
        combination = KeyCombination(test_case.key, test_case.modifiers)

        with pytest.raises(KeyError):
            KeyCombination.parse(combination.display())


class TestParse(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        text: str
        expected: KeyCombination

    test_cases = (
        TestCase(label="a plain key", text="F11", expected=KeyCombination(dpg.mvKey_F1 + 10)),
        TestCase(label="one modifier", text="Ctrl+D", expected=KeyCombination(dpg.mvKey_D, CTRL)),
        TestCase(
            label="two modifiers",
            text="Ctrl+Shift+Z",
            expected=KeyCombination(dpg.mvKey_Z, CTRL_SHIFT),
        ),
        TestCase(
            label="modifiers named out of canonical order",
            text="Shift+Ctrl+Z",
            expected=KeyCombination(dpg.mvKey_Z, CTRL_SHIFT),
        ),
        TestCase(
            label="any capitalization",
            text="ctrl+shift+z",
            expected=KeyCombination(dpg.mvKey_Z, CTRL_SHIFT),
        ),
        TestCase(label="a page key", text="Ctrl+PgDn", expected=KeyCombination(KEY_PAGE_DOWN, CTRL)),
        TestCase(label="the separator alone", text=PLUS, expected=KeyCombination(KEY_PLUS)),
        TestCase(
            label="the separator as the key",
            text="Ctrl++",
            expected=KeyCombination(KEY_PLUS, CTRL),
        ),
        TestCase(label="the key written out", text="Ctrl+Plus", expected=KeyCombination(KEY_PLUS, CTRL)),
        TestCase(label="a keypad key", text=f"Num{PLUS}", expected=KeyCombination(dpg.mvKey_Add)),
        TestCase(label="a keypad key written out", text="NumPlus", expected=KeyCombination(dpg.mvKey_Add)),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_parse(self, test_case: TestCase) -> None:
        assert KeyCombination.parse(test_case.text) == test_case.expected

    @pytest.mark.parametrize("text", ["Hyper+D", "Ctrl+Nonesuch", "Ctrl", ""])
    def test_a_text_naming_no_key_raises(self, text: str) -> None:
        with pytest.raises(KeyError):
            KeyCombination.parse(text)

    @pytest.mark.parametrize("text", WRITTEN_COMBINATIONS)
    def test_a_written_combination_reads_back_as_itself(self, text: str) -> None:
        """A binding written in configuration and one declared in code are one value."""
        assert KeyCombination.parse(text).display() == text

    @pytest.mark.parametrize(
        ("written", "expected"),
        [
            (f"Ctrl{PLUS}{PLUS}", "Ctrl+Plus"),
            ("Ctrl+=", "Ctrl+Plus"),
            ("Shift+Ctrl+Z", "Ctrl+Shift+Z"),
            ("ctrl+pgdn", "Ctrl+PgDn"),
        ],
    )
    def test_a_spelling_reads_back_as_the_one_the_combination_displays_under(
        self,
        written: str,
        expected: str,
    ) -> None:
        """A reader writes a combination however they know it and reads back one canonical form."""
        assert KeyCombination.parse(written).display() == expected


class TestKeyLists(BaseTestSuite):
    """A written list names several combinations apart by commas, and a comma written where a key goes
    is the comma key."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        text: str
        expected: Tuple[KeyCombination, ...]

    test_cases = (
        TestCase(label="nothing", text="", expected=()),
        TestCase(label="one combination", text="Ctrl+Y", expected=(CTRL_Y,)),
        TestCase(label="two combinations", text="Ctrl+Y, Ctrl+Shift+Z", expected=(CTRL_Y, CTRL_SHIFT_Z)),
        TestCase(label="two combinations written tight", text="Ctrl+Y,Ctrl+Shift+Z", expected=(CTRL_Y, CTRL_SHIFT_Z)),
        TestCase(label="a blank between two commas", text="Ctrl+Y,,Ctrl+Shift+Z", expected=(CTRL_Y, CTRL_SHIFT_Z)),
        TestCase(label="the comma as a modified key", text="Ctrl+,", expected=(CTRL_COMMA,)),
        TestCase(label="the comma written out", text="Ctrl+Comma", expected=(CTRL_COMMA,)),
        TestCase(
            label="the comma as a modified key ahead of another", text="Ctrl+,, Ctrl+Y", expected=(CTRL_COMMA, CTRL_Y)
        ),
        TestCase(
            label="the comma as a modified key after another", text="Ctrl+Y, Ctrl+,", expected=(CTRL_Y, CTRL_COMMA)
        ),
        TestCase(label="the plus key ahead of another", text="Ctrl++, Ctrl+Y", expected=(CTRL_PLUS, CTRL_Y)),
        TestCase(label="the comma alone", text=",", expected=(COMMA,)),
        TestCase(label="the comma alone after another", text="Ctrl+Y, ,", expected=(CTRL_Y, COMMA)),
        TestCase(label="a combination named twice", text="Ctrl+Y, Ctrl+Y", expected=(CTRL_Y,)),
        TestCase(label="a combination spelled two ways", text="Ctrl+Y, ctrl+y", expected=(CTRL_Y,)),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_parse_combinations(self, test_case: TestCase) -> None:
        assert parse_combinations(test_case.text) == test_case.expected

    def test_a_displayed_list_reads_back_as_itself(self) -> None:
        combinations = (CTRL_COMMA, COMMA, CTRL_Y)

        assert parse_combinations(display_combinations(combinations)) == combinations

    def test_a_displayed_list_joins_its_combinations_by_the_joiner(self) -> None:
        assert display_combinations((CTRL_Y, CTRL_SHIFT_Z)) == KEY_LIST_JOINER.join(
            (CTRL_Y.display(), CTRL_SHIFT_Z.display())
        )
