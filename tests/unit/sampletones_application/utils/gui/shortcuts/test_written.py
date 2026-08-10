import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, CTRL_SHIFT
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut


class TestResolve:
    def test_a_written_combination_becomes_the_one_a_press_is_matched_against(self) -> None:
        shortcut = WrittenShortcut(combination="Ctrl+Y").resolve()

        assert shortcut.combination == KeyCombination(dpg.mvKey_Y, CTRL)

    def test_every_written_alias_reaches_the_action(self) -> None:
        shortcut = WrittenShortcut(combination="Ctrl+Y", aliases=("Ctrl+Shift+Z",)).resolve()

        assert shortcut.combinations() == (
            KeyCombination(dpg.mvKey_Y, CTRL),
            KeyCombination(dpg.mvKey_Z, CTRL_SHIFT),
        )

    def test_an_entry_left_unassigned_carries_no_combination(self) -> None:
        """An action is written down whether or not a key is assigned to it."""
        shortcut = WrittenShortcut(combination=None).resolve()

        assert shortcut.combinations() == ()

    def test_a_transparent_entry_carries_its_declaration(self) -> None:
        shortcut = WrittenShortcut(combination="Ctrl+PgDn", field_transparent=True).resolve()

        assert shortcut.field_transparent is True

    def test_an_entry_naming_no_key_raises(self) -> None:
        with pytest.raises(KeyError):
            WrittenShortcut(combination="Ctrl+Meta").resolve()


class TestRebound:
    def test_a_rebound_entry_answers_the_combination_the_reader_named(self) -> None:
        entry = WrittenShortcut(combination="Ctrl+Y").rebound("Ctrl+Alt+R")

        assert entry.combination == "Ctrl+Alt+R"

    def test_a_rebound_entry_answers_that_combination_alone(self) -> None:
        entry = WrittenShortcut(combination="Ctrl+Y", aliases=("Ctrl+Shift+Z",)).rebound("Ctrl+Alt+R")

        assert entry.aliases == ()

    def test_an_entry_rebound_to_no_combination_is_left_unbound(self) -> None:
        """A reader takes an action's keys away by giving it none."""
        entry = WrittenShortcut(combination="Ctrl+Y").rebound(None)

        assert entry.combination is None

    def test_a_rebound_entry_keeps_the_transparency_the_action_carries(self) -> None:
        entry = WrittenShortcut(combination="Ctrl+PgDn", field_transparent=True).rebound("Ctrl+Alt+N")

        assert entry.field_transparent is True
