from typing import Any, Dict, Final, List, Optional, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.keybindings import KeybindingsCoordinator
from sampletones_application.paths import LANG_EN
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.shortcuts.ids import (
    EDITABLE_SHORTCUT_CATEGORIES,
    ShortcutId,
)
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.view_model.shared.keybindings import (
    KeybindingRow,
    KeybindingsViewModel,
)
from sampletones_shared.types.callback import VoidCallback
from tests.suite.shortcuts import shipped_catalog, shipped_scheme

SAVE_PROJECT: Final[str] = ShortcutId.SAVE_PROJECT.value
ABOUT_DIALOG: Final[str] = ShortcutId.ABOUT_DIALOG.value
UNDO: Final[str] = ShortcutId.UNDO.value
REDO: Final[str] = ShortcutId.REDO.value

SAVE_COMBINATION: Final[str] = "Ctrl+S"
UNDO_COMBINATION: Final[str] = "Ctrl+Z"
REDO_COMBINATION: Final[str] = "Ctrl+Y"
FREE_COMBINATION: Final[str] = "Ctrl+Alt+B"
UNREADABLE_COMBINATION: Final[str] = "Ctrl+Nonsense"


class _SessionRecorder:
    def __init__(self) -> None:
        self.shortcut_scheme_name = shipped_scheme().name
        self.shortcut_overrides: Dict[str, Optional[str]] = {}
        self.writes: List[Tuple[str, Any]] = []

    def set_shortcut_scheme_name(self, name: str) -> None:
        self.writes.append(("scheme", name))
        self.shortcut_scheme_name = name

    def set_shortcut_overrides(self, overrides: Dict[str, Optional[str]]) -> None:
        self.writes.append(("overrides", overrides))
        self.shortcut_overrides = overrides


class _SourceRecorder:
    def __init__(self) -> None:
        self.scheme = shipped_scheme()
        self.activated: List[ShortcutScheme] = []

    def activate(self, scheme: ShortcutScheme) -> None:
        self.activated.append(scheme)
        self.scheme = scheme


class _WindowRecorder:
    """Stands in for the dialog window, with the modal hand-off collapsed to a direct call."""

    def __init__(self) -> None:
        self.view_models: List[KeybindingsViewModel] = []
        self.visible = False
        self.on_scheme_selected: Any = None
        self.on_action_selected: Any = None
        self.on_combination_typed: Any = None
        self.on_combination_captured: Any = None
        self.on_clear: Any = None
        self.on_reset: Any = None
        self.on_commit: Any = None
        self.on_cancel: Any = None

    def open(self, view_model: KeybindingsViewModel) -> None:
        self.visible = True
        self.view_models.append(view_model)

    def update_view(self, view_model: KeybindingsViewModel) -> None:
        self.view_models.append(view_model)

    def yield_to(self, raise_modal: VoidCallback) -> None:
        self.visible = False
        raise_modal()

    def resume(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    @property
    def view_model(self) -> KeybindingsViewModel:
        return self.view_models[-1]


class _DialogsRecorder:
    def __init__(self) -> None:
        self.confirmations: List[Dict[str, Any]] = []

    def show_confirmation(self, **kwargs: Any) -> None:
        self.confirmations.append(kwargs)

    def confirm(self) -> None:
        self.confirmations[-1]["on_confirm"]()

    def decline(self) -> None:
        self.confirmations[-1]["on_cancel"]()


class Harness:
    """The coordinator wired to recorders, with the gestures a user makes spelled as methods."""

    def __init__(self) -> None:
        self.session = _SessionRecorder()
        self.source = _SourceRecorder()
        self.window = _WindowRecorder()
        self.dialogs = _DialogsRecorder()
        self.coordinator = KeybindingsCoordinator(
            self.session,
            self.source,
            shipped_catalog(),
            window=self.window,
            dialogs=self.dialogs,
            language_manager=LanguageManager(LANG_EN),
        )

    def open(self) -> None:
        self.coordinator.open()

    def select(self, action: str) -> None:
        self.window.on_action_selected(action)

    def type_combination(self, text: str) -> None:
        self.window.on_combination_typed(text)

    def capture(self, text: str) -> None:
        self.window.on_combination_captured(KeyCombination.parse(text))

    def clear(self) -> None:
        self.window.on_clear()

    def reset(self) -> None:
        self.window.on_reset()

    def commit(self) -> None:
        self.window.on_commit()

    def cancel(self) -> None:
        self.window.on_cancel()

    def select_scheme(self, name: str) -> None:
        self.window.on_scheme_selected(name)

    def row(self, action: str) -> KeybindingRow:
        for group in self.window.view_model.groups:
            for row in group.rows:
                if row.action == action:
                    return row

        raise AssertionError(f"The dialog lists no row for {action!r}")


@pytest.fixture(name="harness")
def harness_fixture() -> Harness:
    harness = Harness()
    harness.open()
    return harness


class TestOpening:
    def test_the_dialog_shows_the_keys_in_force(self, harness: Harness) -> None:
        assert harness.row(SAVE_PROJECT).combination == SAVE_COMBINATION

    def test_an_unbound_action_is_listed_carrying_no_keys(self, harness: Harness) -> None:
        assert harness.row(ABOUT_DIALOG).combination == ""

    def test_every_editable_scope_is_listed(self, harness: Harness) -> None:
        assert tuple(group.category for group in harness.window.view_model.groups) == tuple(
            category.value for category in EDITABLE_SHORTCUT_CATEGORIES
        )

    def test_every_editable_action_reaches_a_row(self, harness: Harness) -> None:
        listed = {row.action for group in harness.window.view_model.groups for row in group.rows}
        editable = {
            shortcut_id.value for shortcut_id in ShortcutId if shortcut_id.category in EDITABLE_SHORTCUT_CATEGORIES
        }

        assert listed == editable

    def test_every_row_carries_a_label_a_reader_sees(self, harness: Harness) -> None:
        unlabelled = [row.action for group in harness.window.view_model.groups for row in group.rows if not row.label]

        assert unlabelled == []

    def test_every_shipped_scheme_is_offered(self, harness: Harness) -> None:
        assert harness.window.view_model.schemes == shipped_catalog().names

    def test_the_stored_preference_reaches_the_dialog(self) -> None:
        harness = Harness()
        harness.session.shortcut_overrides = {SAVE_PROJECT: FREE_COMBINATION}
        harness.open()

        assert harness.row(SAVE_PROJECT).combination == FREE_COMBINATION


class TestSelection:
    def test_selecting_an_action_puts_its_keys_in_the_entry_box(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)

        assert harness.window.view_model.selected == SAVE_PROJECT
        assert harness.window.view_model.combination == SAVE_COMBINATION

    def test_an_unbound_action_leaves_the_entry_box_empty(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)

        assert harness.window.view_model.combination == ""

    def test_a_combination_arriving_with_nothing_selected_is_refused(self, harness: Harness) -> None:
        with pytest.raises(SystemError):
            harness.type_combination(FREE_COMBINATION)


class TestAssignment:
    def test_a_written_combination_reaches_the_action(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)

        assert harness.row(ABOUT_DIALOG).combination == FREE_COMBINATION

    def test_a_written_combination_reads_back_the_way_it_is_displayed(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination("shift+ctrl+alt+b")

        assert harness.row(ABOUT_DIALOG).combination == "Ctrl+Alt+Shift+B"

    def test_a_captured_press_reaches_the_action(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.capture(FREE_COMBINATION)

        assert harness.row(ABOUT_DIALOG).combination == FREE_COMBINATION

    def test_a_combination_naming_no_key_is_reported_and_the_keys_stand(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(UNREADABLE_COMBINATION)

        assert UNREADABLE_COMBINATION in harness.window.view_model.message
        assert harness.row(SAVE_PROJECT).combination == SAVE_COMBINATION

    def test_a_later_assignment_clears_the_message(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(UNREADABLE_COMBINATION)
        harness.type_combination(FREE_COMBINATION)

        assert harness.window.view_model.message == ""

    def test_nothing_reaches_the_keys_in_force_before_it_is_confirmed(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)

        assert harness.source.activated == []
        assert harness.session.writes == []


class TestTakenCombination:
    def test_assigning_keys_another_action_holds_asks_first(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)

        assert len(harness.dialogs.confirmations) == 1
        assert harness.row(ABOUT_DIALOG).combination == ""

    def test_the_prompt_names_the_action_the_keys_are_taken_from(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)

        assert "Save project" in harness.dialogs.confirmations[-1]["message"]

    def test_the_dialog_steps_aside_so_the_prompt_can_open(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)

        assert not harness.window.visible

    def test_confirming_takes_the_keys_and_leaves_the_holder_unbound(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)
        harness.dialogs.confirm()

        assert harness.row(ABOUT_DIALOG).combination == SAVE_COMBINATION
        assert harness.row(SAVE_PROJECT).combination == ""
        assert harness.window.visible

    def test_declining_leaves_both_actions_on_the_keys_they_had(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)
        harness.dialogs.decline()

        assert harness.row(ABOUT_DIALOG).combination == ""
        assert harness.row(SAVE_PROJECT).combination == SAVE_COMBINATION
        assert harness.window.visible

    def test_an_alias_another_action_answers_is_taken_the_same_way(self, harness: Harness) -> None:
        """Redo answers Ctrl+Shift+Z beside its own keys, which an assignment takes with them."""
        harness.select(ABOUT_DIALOG)
        harness.type_combination("Ctrl+Shift+Z")
        harness.dialogs.confirm()

        assert harness.row(ABOUT_DIALOG).combination == "Ctrl+Shift+Z"
        assert harness.row(ShortcutId.REDO.value).combination == ""

    def test_the_keys_an_action_already_answers_are_assigned_without_asking(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(SAVE_COMBINATION)

        assert harness.dialogs.confirmations == []
        assert harness.row(SAVE_PROJECT).combination == SAVE_COMBINATION


class TestClear:
    def test_clearing_leaves_the_action_unbound(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.clear()

        assert harness.row(SAVE_PROJECT).combination == ""

    def test_the_keys_a_cleared_action_held_are_free_to_take(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.clear()
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)

        assert harness.dialogs.confirmations == []
        assert harness.row(ABOUT_DIALOG).combination == SAVE_COMBINATION


class TestReset:
    def test_resetting_asks_first(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(FREE_COMBINATION)
        harness.reset()

        assert len(harness.dialogs.confirmations) == 1
        assert not harness.window.visible

    def test_confirming_puts_every_action_back_on_the_shipped_keys(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(FREE_COMBINATION)
        harness.reset()
        harness.dialogs.confirm()

        assert harness.row(SAVE_PROJECT).combination == SAVE_COMBINATION
        assert harness.window.visible

    def test_declining_leaves_the_edits_standing(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(FREE_COMBINATION)
        harness.reset()
        harness.dialogs.decline()

        assert harness.row(SAVE_PROJECT).combination == FREE_COMBINATION

    def test_a_reset_stores_no_overrides(self, harness: Harness) -> None:
        harness.select(SAVE_PROJECT)
        harness.type_combination(FREE_COMBINATION)
        harness.reset()
        harness.dialogs.confirm()
        harness.commit()

        assert dict(harness.session.writes)["overrides"] == {}


class TestCommit:
    def test_confirming_puts_the_edited_keys_in_force(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)
        harness.commit()

        assert harness.source.scheme.shortcut(ShortcutId.ABOUT_DIALOG).display() == FREE_COMBINATION

    def test_confirming_stores_the_rebound_actions_and_nothing_else(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)
        harness.commit()

        assert dict(harness.session.writes)["overrides"] == {ABOUT_DIALOG: FREE_COMBINATION}

    def test_a_displaced_action_is_stored_as_unbound(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)
        harness.dialogs.confirm()
        harness.commit()

        assert dict(harness.session.writes)["overrides"] == {
            ABOUT_DIALOG: SAVE_COMBINATION,
            SAVE_PROJECT: None,
        }

    def test_confirming_stores_the_scheme_the_dialog_worked_from(self, harness: Harness) -> None:
        harness.commit()

        assert dict(harness.session.writes)["scheme"] == shipped_scheme().name

    def test_confirming_closes_the_dialog(self, harness: Harness) -> None:
        harness.commit()

        assert not harness.window.visible

    def test_a_stored_preference_reopens_on_the_keys_it_stored(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(SAVE_COMBINATION)
        harness.dialogs.confirm()
        harness.commit()
        harness.open()

        assert harness.row(ABOUT_DIALOG).combination == SAVE_COMBINATION
        assert harness.row(SAVE_PROJECT).combination == ""


class TestCancel:
    def test_cancelling_an_untouched_dialog_closes_it_without_asking(self, harness: Harness) -> None:
        harness.cancel()

        assert harness.dialogs.confirmations == []
        assert not harness.window.visible

    def test_cancelling_an_edited_dialog_asks_first(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)
        harness.cancel()

        assert len(harness.dialogs.confirmations) == 1
        assert not harness.window.visible

    def test_keeping_the_edit_brings_the_dialog_back(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)
        harness.cancel()
        harness.dialogs.decline()

        assert harness.window.visible
        assert harness.row(ABOUT_DIALOG).combination == FREE_COMBINATION

    def test_discarding_leaves_the_keys_in_force_alone(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)
        harness.cancel()
        harness.dialogs.confirm()

        assert harness.source.activated == []
        assert harness.session.writes == []
        assert not harness.window.visible

    def test_editing_a_closed_dialog_is_refused(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.cancel()

        with pytest.raises(SystemError):
            harness.type_combination(FREE_COMBINATION)


class TestScheme:
    def test_choosing_the_scheme_already_open_leaves_the_edits_standing(self, harness: Harness) -> None:
        harness.select(ABOUT_DIALOG)
        harness.type_combination(FREE_COMBINATION)
        harness.select_scheme(shipped_scheme().name)

        assert harness.row(ABOUT_DIALOG).combination == FREE_COMBINATION

    def test_an_unknown_scheme_falls_back_to_the_one_the_build_defaults_to(self, harness: Harness) -> None:
        harness.select_scheme("nonexistent")

        assert harness.window.view_model.scheme == shipped_scheme().name


class TestTrade:
    """Two actions passing keys between them, which is what a displaced holder makes room for."""

    @pytest.fixture(name="traded")
    def traded_fixture(self, harness: Harness) -> Harness:
        harness.select(UNDO)
        harness.type_combination(REDO_COMBINATION)
        harness.dialogs.confirm()
        harness.select(REDO)
        harness.type_combination(UNDO_COMBINATION)
        return harness

    def test_each_action_arrives_at_the_keys_the_other_left(self, traded: Harness) -> None:
        assert traded.row(UNDO).combination == REDO_COMBINATION
        assert traded.row(REDO).combination == UNDO_COMBINATION

    def test_the_traded_keys_reach_the_scheme_put_in_force(self, traded: Harness) -> None:
        traded.commit()

        assert traded.source.scheme.shortcut(ShortcutId.UNDO).display() == REDO_COMBINATION
        assert traded.source.scheme.shortcut(ShortcutId.REDO).display() == UNDO_COMBINATION

    def test_a_stored_trade_reopens_on_the_keys_it_stored(self, traded: Harness) -> None:
        traded.commit()
        traded.open()

        assert traded.row(UNDO).combination == REDO_COMBINATION
        assert traded.row(REDO).combination == UNDO_COMBINATION
