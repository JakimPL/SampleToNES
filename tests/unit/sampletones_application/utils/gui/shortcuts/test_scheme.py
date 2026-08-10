from pathlib import Path

import dearpygui.dearpygui as dpg
import pytest
from pydantic import ValidationError

from sampletones_application.constants.keybindings import DEFAULT_SCHEME_NAME
from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, CTRL_SHIFT
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut
from sampletones_core.paths import EXT_FILE_YAML
from tests.unit.sampletones_application.utils.gui.shortcuts.conftest import (
    PROBE_SCHEME_NAME,
    RebindScheme,
)

SHIPPED_FILE = KEYBINDINGS_DIRECTORY / f"{DEFAULT_SCHEME_NAME}{EXT_FILE_YAML}"

TABLE_COMBINATION = "Del"

UNNAMED_KEY = -1

_PARTIAL_SCHEME_FILE = """
name: minimal
bindings:
  Play: {combination: "Space"}
"""


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestBindings:
    def test_an_action_reads_the_binding_the_scheme_gives_it(self, rebound: RebindScheme) -> None:
        scheme = rebound({ShortcutId.UNDO: WrittenShortcut(combination="Ctrl+Z")})

        assert scheme.shortcut(ShortcutId.UNDO).combination == KeyCombination(dpg.mvKey_Z, CTRL)

    def test_an_alias_reaches_the_action_beside_the_combination_it_displays(
        self,
        rebound: RebindScheme,
    ) -> None:
        scheme = rebound(
            {
                ShortcutId.REDO: WrittenShortcut(
                    combination="Ctrl+Y",
                    aliases=("Ctrl+Shift+Z",),
                ),
            },
        )

        assert scheme.shortcut(ShortcutId.REDO).combinations() == (
            KeyCombination(dpg.mvKey_Y, CTRL),
            KeyCombination(dpg.mvKey_Z, CTRL_SHIFT),
        )


class TestCompleteness:
    def test_a_scheme_answering_every_action_is_accepted(self, rebound: RebindScheme) -> None:
        assert rebound({}).name == PROBE_SCHEME_NAME

    def test_a_scheme_leaving_an_action_unanswered_raises(self, shipped: ShortcutScheme) -> None:
        """Every action is answered, so a menu and a panel find an entry for whatever they ask."""
        bindings = {
            shortcut_id: written
            for shortcut_id, written in shipped.bindings.items()
            if shortcut_id is not ShortcutId.PLAY
        }

        with pytest.raises(SystemError):
            ShortcutScheme(name=PROBE_SCHEME_NAME, bindings=bindings)

    def test_a_scheme_naming_an_action_the_application_has_none_of_raises(self) -> None:
        with pytest.raises(ValidationError):
            ShortcutScheme.model_validate(
                {
                    "name": PROBE_SCHEME_NAME,
                    "bindings": {"PlayLouder": {"combination": "Ctrl+K"}},
                },
            )


class TestCollisions:
    def test_two_actions_of_one_category_claiming_a_combination_raises(
        self,
        rebound: RebindScheme,
    ) -> None:
        """A press reaches one action, so the scheme states which one before the application runs."""
        with pytest.raises(SystemError):
            rebound({ShortcutId.UNDO: WrittenShortcut(combination="Ctrl+Y")})

    def test_an_alias_claiming_another_action_s_combination_raises(self, rebound: RebindScheme) -> None:
        with pytest.raises(SystemError):
            rebound(
                {
                    ShortcutId.UNDO: WrittenShortcut(
                        combination="Ctrl+K",
                        aliases=("Ctrl+Shift+Z",),
                    ),
                },
            )

    def test_one_combination_serves_a_category_of_its_own(self, rebound: RebindScheme) -> None:
        """Tab moves between dialog controls and between tracker columns, each in its own scope."""
        scheme = rebound({ShortcutId.SAMPLES_RENAME_SAMPLE: WrittenShortcut(combination="Tab")})

        assert scheme.shortcut(ShortcutId.TRACKER_NEXT_COLUMN).display() == "Tab"
        assert scheme.shortcut(ShortcutId.SAMPLES_RENAME_SAMPLE).display() == "Tab"

    def test_a_combination_naming_no_key_raises(self, rebound: RebindScheme) -> None:
        with pytest.raises(KeyError):
            rebound({ShortcutId.PLAY: WrittenShortcut(combination="Ctrl+Meta")})


class TestAction:
    def test_a_press_resolves_to_the_action_its_category_binds_it_to(self, shipped: ShortcutScheme) -> None:
        assert shipped.action(ShortcutCategory.ORDER, _press("Alt+Left")) is ShortcutId.ORDER_MOVE_FRAME_LEFT

    def test_an_alias_resolves_to_the_action_it_extends(self, shipped: ShortcutScheme) -> None:
        assert shipped.action(ShortcutCategory.ORDER, _press("Num+")) is ShortcutId.ORDER_INSERT_FRAME

    def test_a_press_the_category_leaves_unnamed_resolves_to_nothing(self, shipped: ShortcutScheme) -> None:
        assert shipped.action(ShortcutCategory.SAMPLES, _press("Ctrl+S")) is None

    def test_each_category_answers_a_shared_combination_with_its_own_action(
        self,
        shipped: ShortcutScheme,
    ) -> None:
        """Escape cancels a pending entry in either editing scope and cancels a dialog in a modal."""
        assert shipped.action(ShortcutCategory.ORDER, _press("Esc")) is ShortcutId.ORDER_CANCEL_ENTRY
        assert shipped.action(ShortcutCategory.TRACKER, _press("Esc")) is ShortcutId.TRACKER_CANCEL_ENTRY
        assert shipped.action(ShortcutCategory.DIALOG, _press("Esc")) is ShortcutId.DIALOG_CANCEL

    def test_a_modifier_the_combination_omits_leaves_the_press_unnamed(self, shipped: ShortcutScheme) -> None:
        """A binding names the modifiers held with it, so Shift+Left is not the plain Left move."""
        assert shipped.action(ShortcutCategory.ORDER, _press("Shift+Left")) is None


class TestClaimant:
    def test_a_combination_the_category_binds_reads_as_the_action_it_reaches(self, shipped: ShortcutScheme) -> None:
        claimant = shipped.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Z"))

        assert claimant is ShortcutId.UNDO

    def test_an_alias_reads_as_the_action_it_extends(self, shipped: ShortcutScheme) -> None:
        claimant = shipped.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Shift+Z"))

        assert claimant is ShortcutId.REDO

    def test_a_combination_the_category_leaves_unclaimed_reads_as_nothing(self, shipped: ShortcutScheme) -> None:
        assert shipped.claimant(ShortcutCategory.SAMPLES, KeyCombination.parse("Ctrl+Z")) is None

    def test_each_category_answers_a_shared_combination_with_its_own_action(self, shipped: ShortcutScheme) -> None:
        escape = KeyCombination.parse("Esc")

        assert shipped.claimant(ShortcutCategory.TRACKER, escape) is ShortcutId.TRACKER_CANCEL_ENTRY
        assert shipped.claimant(ShortcutCategory.DIALOG, escape) is ShortcutId.DIALOG_CANCEL


class TestWithBinding:
    def test_an_action_answers_the_combination_it_is_given(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_binding(ShortcutId.UNDO, KeyCombination.parse("Ctrl+Alt+U"))

        assert scheme.shortcut(ShortcutId.UNDO).display() == "Ctrl+Alt+U"

    def test_an_action_answers_that_combination_alone(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_binding(ShortcutId.ORDER_INSERT_FRAME, KeyCombination.parse("Ctrl+Alt+I"))

        assert scheme.shortcut(ShortcutId.ORDER_INSERT_FRAME).aliases == ()

    def test_an_action_given_no_combination_is_left_unbound(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_binding(ShortcutId.UNDO, None)

        assert scheme.shortcut(ShortcutId.UNDO).combinations() == ()

    def test_a_combination_the_category_already_answers_raises(self, shipped: ShortcutScheme) -> None:
        """An editor is told which action holds the keys, so the reader decides who keeps them."""
        with pytest.raises(SystemError):
            shipped.with_binding(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+S"))

    def test_a_combination_another_category_holds_stands(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_binding(ShortcutId.ABOUT_DIALOG, KeyCombination.parse(TABLE_COMBINATION))
        combination = KeyCombination.parse(TABLE_COMBINATION)

        assert scheme.claimant(ShortcutCategory.APPLICATION, combination) is ShortcutId.ABOUT_DIALOG

    def test_a_combination_naming_no_key_raises(self, shipped: ShortcutScheme) -> None:
        with pytest.raises(KeyError):
            shipped.with_binding(ShortcutId.UNDO, KeyCombination(UNNAMED_KEY))


class TestWithBindings:
    def test_two_actions_trade_the_combinations_they_held(self, shipped: ShortcutScheme) -> None:
        """A whole set is read at once, so a swap arrives without either action holding both keys."""
        scheme = shipped.with_bindings(
            {
                ShortcutId.UNDO: KeyCombination.parse("Ctrl+Y"),
                ShortcutId.REDO: KeyCombination.parse("Ctrl+Z"),
            },
        )

        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Y")) is ShortcutId.UNDO
        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Z")) is ShortcutId.REDO

    def test_the_actions_no_binding_names_keep_the_scheme_s_keys(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_bindings({ShortcutId.UNDO: KeyCombination.parse("Ctrl+Alt+U")})

        assert scheme.shortcut(ShortcutId.REDO) == shipped.shortcut(ShortcutId.REDO)


class TestWithOverrides:
    def test_an_override_gives_the_action_the_keys_it_names(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_overrides({"Undo": "Ctrl+Alt+U"})

        assert scheme.shortcut(ShortcutId.UNDO).display() == "Ctrl+Alt+U"
        assert scheme.action(ShortcutCategory.APPLICATION, _press("Ctrl+Alt+U")) is ShortcutId.UNDO

    def test_the_keys_the_override_replaces_stop_reaching_the_action(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_overrides({"Undo": "Ctrl+Alt+U"})

        assert scheme.action(ShortcutCategory.APPLICATION, _press("Ctrl+Z")) is None

    def test_an_override_states_the_whole_of_what_reaches_the_action(self, shipped: ShortcutScheme) -> None:
        """A reader names one combination, so the keypad alias the scheme shipped goes with it."""
        scheme = shipped.with_overrides({"OrderInsertFrame": "Ctrl+Alt+I"})

        assert scheme.shortcut(ShortcutId.ORDER_INSERT_FRAME).aliases == ()
        assert scheme.action(ShortcutCategory.ORDER, _press("Num+")) is None

    def test_a_rebound_action_keeps_the_transparency_its_role_carries(self, shipped: ShortcutScheme) -> None:
        """Switching tabs outranks text entry whichever keys it answers to."""
        scheme = shipped.with_overrides({"NextTab": "Ctrl+Alt+N"})

        assert scheme.shortcut(ShortcutId.NEXT_TAB).field_transparent

    def test_the_actions_no_override_names_keep_the_scheme_s_keys(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_overrides({"Undo": "Ctrl+Alt+U"})

        assert scheme.shortcut(ShortcutId.REDO) == shipped.shortcut(ShortcutId.REDO)

    def test_an_override_naming_an_action_the_build_has_none_of_is_left_out(self, shipped: ShortcutScheme) -> None:
        """A preference outlives the build that stored it, so a stale entry costs only itself."""
        scheme = shipped.with_overrides({"PlayLouder": "Ctrl+K", "Undo": "Ctrl+Alt+U"})

        assert scheme.shortcut(ShortcutId.UNDO).display() == "Ctrl+Alt+U"

    def test_an_override_naming_no_key_is_left_out(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_overrides({"Undo": "Ctrl+Gibberish"})

        assert scheme.shortcut(ShortcutId.UNDO) == shipped.shortcut(ShortcutId.UNDO)

    def test_an_override_its_category_already_answers_is_left_out(self, shipped: ShortcutScheme) -> None:
        """One press reaches one action, so an override claiming a taken combination stands aside."""
        scheme = shipped.with_overrides({"AboutDialog": "Ctrl+S"})

        assert scheme.action(ShortcutCategory.APPLICATION, _press("Ctrl+S")) is ShortcutId.SAVE_PROJECT
        assert scheme.shortcut(ShortcutId.ABOUT_DIALOG) == shipped.shortcut(ShortcutId.ABOUT_DIALOG)

    def test_an_override_taking_a_combination_another_category_holds_stands(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_overrides({"AboutDialog": TABLE_COMBINATION})

        assert scheme.action(ShortcutCategory.APPLICATION, _press(TABLE_COMBINATION)) is ShortcutId.ABOUT_DIALOG
        assert scheme.action(ShortcutCategory.SAMPLES, _press(TABLE_COMBINATION)) is ShortcutId.SAMPLES_REMOVE_SAMPLE

    def test_an_override_stating_no_combination_leaves_the_action_unbound(self, shipped: ShortcutScheme) -> None:
        scheme = shipped.with_overrides({"Undo": None})

        assert scheme.shortcut(ShortcutId.UNDO).combinations() == ()

    def test_overrides_passing_a_combination_between_two_actions_both_stand(
        self,
        shipped: ShortcutScheme,
    ) -> None:
        """An editor stores the action it displaced beside the one that took its keys."""
        scheme = shipped.with_overrides({"AboutDialog": "Ctrl+S", "SaveProject": None})

        assert scheme.action(ShortcutCategory.APPLICATION, _press("Ctrl+S")) is ShortcutId.ABOUT_DIALOG
        assert scheme.shortcut(ShortcutId.SAVE_PROJECT).combinations() == ()

    def test_a_scheme_without_overrides_is_the_one_it_started_as(self, shipped: ShortcutScheme) -> None:
        assert shipped.with_overrides({}) is shipped


class TestLoad:
    def test_a_file_is_read_as_the_scheme_it_holds(self, tmp_path: Path) -> None:
        path = tmp_path / "copy.yaml"
        path.write_text(SHIPPED_FILE.read_text())

        assert ShortcutScheme.load(path).name == DEFAULT_SCHEME_NAME

    def test_a_file_answering_part_of_the_actions_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "minimal.yaml"
        path.write_text(_PARTIAL_SCHEME_FILE)

        with pytest.raises(SystemError):
            ShortcutScheme.load(path)

    def test_a_file_holding_no_mapping_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "list.yaml"
        path.write_text("- Play\n")

        with pytest.raises(TypeError):
            ShortcutScheme.load(path)

    def test_an_absent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SystemError):
            ShortcutScheme.load(tmp_path / "absent.yaml")
