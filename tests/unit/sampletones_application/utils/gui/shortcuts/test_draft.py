from dataclasses import dataclass
from typing import Dict, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.keys import (
    KEY_DISPLAY_NAMES,
    KEY_MODIFIER_ALT,
    KEY_MODIFIER_CTRL,
)
from sampletones_application.utils.gui.keyboard.modifiers import ALT, CTRL, NO_MODIFIERS
from sampletones_application.utils.gui.shortcuts.draft import ShortcutDraft
from sampletones_application.utils.gui.shortcuts.ids import ShortcutCategory, ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

FREE_COMBINATION = "Ctrl+Alt+B"
TABLE_COMBINATION = "Del"

UNNAMED_KEY = -1


@pytest.fixture
def draft(shipped: ShortcutScheme) -> ShortcutDraft:
    """A draft of the shipped scheme, opened on a session that stores no preference of its own."""
    return ShortcutDraft.open(shipped, {})


class TestOpen:
    def test_a_session_storing_nothing_opens_on_the_keys_the_scheme_ships(self, draft: ShortcutDraft) -> None:
        assert draft.combination(ShortcutId.UNDO) == KeyCombination.parse("Ctrl+Z")

    def test_a_draft_opens_on_what_the_session_holds(self, shipped: ShortcutScheme) -> None:
        """A dialog asks whether the reader changed anything, which counts from the moment it opened."""
        assert ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"}).is_dirty is False

    def test_a_stored_override_opens_as_the_keys_its_action_answers(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"})

        assert draft.combination(ShortcutId.UNDO) == KeyCombination.parse("Ctrl+Alt+U")

    def test_a_stored_override_reads_back_as_the_preference_it_came_from(self, shipped: ShortcutScheme) -> None:
        overrides: Dict[str, Optional[str]] = {"Undo": "Ctrl+Alt+U"}

        assert ShortcutDraft.open(shipped, overrides).overrides() == overrides

    def test_a_stored_override_stating_no_combination_opens_unbound(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": None})

        assert draft.combination(ShortcutId.UNDO) is None

    def test_a_stored_override_dropping_the_aliases_alone_opens_as_an_edit(self, shipped: ShortcutScheme) -> None:
        """An override states the whole of what reaches an action, so the aliases go with it."""
        draft = ShortcutDraft.open(shipped, {"OrderInsertFrame": "Plus"})

        assert draft.overrides() == {"OrderInsertFrame": "Plus"}

    def test_a_stored_override_this_build_carries_no_action_for_stays_behind(self, shipped: ShortcutScheme) -> None:
        """A preference outlives the build that stored it, so a stale entry costs only itself."""
        draft = ShortcutDraft.open(shipped, {"PlayLouder": "Ctrl+K", "Undo": "Ctrl+Alt+U"})

        assert draft.overrides() == {"Undo": "Ctrl+Alt+U"}

    def test_a_stored_override_its_category_already_answers_stays_behind(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"AboutDialog": "Ctrl+S"})

        assert draft.overrides() == {}


class TestCombination:
    def test_an_untouched_action_reads_the_keys_the_scheme_gives_it(self, draft: ShortcutDraft) -> None:
        assert draft.combination(ShortcutId.SAVE_PROJECT) == KeyCombination.parse("Ctrl+S")

    def test_an_assigned_action_reads_the_keys_the_reader_gave_it(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION))

        assert edited.combination(ShortcutId.UNDO) == KeyCombination.parse(FREE_COMBINATION)

    def test_a_cleared_action_reads_as_unbound(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(ShortcutId.UNDO)

        assert edited.combination(ShortcutId.UNDO) is None

    def test_an_action_the_scheme_leaves_unbound_reads_as_unbound(self, draft: ShortcutDraft) -> None:
        assert draft.combination(ShortcutId.ABOUT_DIALOG) is None


class TestClaimant:
    def test_the_action_holding_a_combination_answers_for_it(self, draft: ShortcutDraft) -> None:
        claimant = draft.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+S"))

        assert claimant is ShortcutId.SAVE_PROJECT

    def test_an_alias_is_held_as_firmly_as_the_combination_it_extends(self, draft: ShortcutDraft) -> None:
        """An assignment takes every key that reaches the holder, aliases included."""
        claimant = draft.claimant(ShortcutId.ORDER_ADD_FRAME, KeyCombination.parse("NumPlus"))

        assert claimant is ShortcutId.ORDER_INSERT_FRAME

    def test_a_combination_no_action_of_the_category_holds_is_free(self, draft: ShortcutDraft) -> None:
        assert draft.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse(FREE_COMBINATION)) is None

    def test_a_combination_another_category_holds_is_free(self, draft: ShortcutDraft) -> None:
        assert draft.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse(TABLE_COMBINATION)) is None

    def test_an_action_holds_its_own_keys_against_no_one(self, draft: ShortcutDraft) -> None:
        """Giving an action the keys it already answers is the reader confirming them."""
        assert draft.claimant(ShortcutId.UNDO, KeyCombination.parse("Ctrl+Z")) is None

    def test_the_keys_an_edit_left_behind_are_free(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION))

        assert edited.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+Z")) is None

    def test_the_aliases_an_edit_left_behind_are_free(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.ORDER_INSERT_FRAME, KeyCombination.parse("Ctrl+Alt+I"))

        assert edited.claimant(ShortcutId.ORDER_ADD_FRAME, KeyCombination.parse("NumPlus")) is None


class TestAssign(BaseTestSuite):
    """An assignment takes the combination from whichever action of the category holds it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shortcut_id: ShortcutId
        written: str
        holder: ShortcutId

    test_cases = (
        TestCase(
            label="a combination another action displays",
            shortcut_id=ShortcutId.ABOUT_DIALOG,
            written="Ctrl+S",
            holder=ShortcutId.SAVE_PROJECT,
        ),
        TestCase(
            label="an alias another action answers",
            shortcut_id=ShortcutId.ORDER_ADD_FRAME,
            written="NumPlus",
            holder=ShortcutId.ORDER_INSERT_FRAME,
        ),
        TestCase(
            label="a combination held in another category too",
            shortcut_id=ShortcutId.SAMPLES_MOVE_SAMPLE_UP,
            written="F2",
            holder=ShortcutId.SAMPLES_RENAME_SAMPLE,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_action_that_held_the_combination_is_left_unbound(
        self,
        test_case: TestCase,
        draft: ShortcutDraft,
    ) -> None:
        edited = draft.assign(test_case.shortcut_id, KeyCombination.parse(test_case.written))

        assert edited.combination(test_case.holder) is None

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_scheme_the_assignment_produces_reaches_the_action_it_named(
        self,
        test_case: TestCase,
        draft: ShortcutDraft,
    ) -> None:
        combination = KeyCombination.parse(test_case.written)
        scheme = draft.assign(test_case.shortcut_id, combination).scheme()

        assert scheme.claimant(test_case.shortcut_id.category, combination) is test_case.shortcut_id

    def test_an_assignment_leaves_the_draft_holding_keys_to_store(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION))

        assert edited.is_dirty is True

    def test_the_actions_an_assignment_leaves_alone_keep_their_keys(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION))

        assert edited.combination(ShortcutId.REDO) == KeyCombination.parse("Ctrl+Y")

    def test_an_action_given_the_keys_it_already_answers_keeps_them(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse("Ctrl+Z"))

        assert edited.combination(ShortcutId.UNDO) == KeyCombination.parse("Ctrl+Z")


class TestUnwritableCombination(BaseTestSuite):
    """An edit is held to the keys the table names, which is what a stored preference is written in.

    A press reports whatever code the keyboard sends — a modifier arrives under a code of its own,
    and a keyboard carries keys past the ones a binding is spelled with — so a combination reaches
    the draft that no scheme could hold.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        combination: KeyCombination

    test_cases = (
        TestCase(
            label="the code reserved for alt",
            combination=KeyCombination(KEY_MODIFIER_ALT, ALT),
        ),
        TestCase(
            label="the code reserved for control",
            combination=KeyCombination(KEY_MODIFIER_CTRL, CTRL),
        ),
        TestCase(
            label="a key the table names none of",
            combination=KeyCombination(dpg.mvKey_Browser_Back, NO_MODIFIERS),
        ),
        TestCase(
            label="a code no key carries",
            combination=KeyCombination(UNNAMED_KEY, CTRL),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_assigning_it_is_refused(self, test_case: TestCase, draft: ShortcutDraft) -> None:
        with pytest.raises(KeyError):
            draft.assign(ShortcutId.UNDO, test_case.combination)

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_action_keeps_the_keys_it_had(self, test_case: TestCase, draft: ShortcutDraft) -> None:
        with pytest.raises(KeyError):
            draft.assign(ShortcutId.UNDO, test_case.combination)

        assert draft.combination(ShortcutId.UNDO) == KeyCombination.parse("Ctrl+Z")
        assert draft.is_dirty is False

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_it_reaches_no_action_of_the_scope(self, test_case: TestCase, draft: ShortcutDraft) -> None:
        """A combination no action can be given is one no action holds, so none is asked for it."""
        assert draft.claimant(ShortcutId.UNDO, test_case.combination) is None


class TestClear:
    def test_a_cleared_action_stores_as_unbound(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(ShortcutId.UNDO)

        assert edited.overrides() == {"Undo": None}

    def test_the_keys_a_cleared_action_held_are_free_for_another(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(ShortcutId.UNDO)

        assert edited.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+Z")) is None

    def test_the_scheme_a_cleared_action_produces_leaves_its_keys_unclaimed(self, draft: ShortcutDraft) -> None:
        scheme = draft.clear(ShortcutId.UNDO).scheme()

        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Z")) is None


class TestReset:
    def test_a_reset_draft_reads_the_keys_the_scheme_ships(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"}).reset()

        assert draft.combination(ShortcutId.UNDO) == KeyCombination.parse("Ctrl+Z")

    def test_a_reset_draft_stores_no_override(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"}).reset()

        assert draft.overrides() == {}

    def test_a_reset_over_a_stored_preference_leaves_keys_to_store(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"}).reset()

        assert draft.is_dirty is True

    def test_a_reset_of_a_draft_on_the_shipped_keys_leaves_it_as_it_was(self, draft: ShortcutDraft) -> None:
        assert draft.reset().is_dirty is False


class TestScheme:
    def test_the_scheme_answers_the_keys_the_reader_gave(self, draft: ShortcutDraft) -> None:
        scheme = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION)).scheme()

        assert scheme.shortcut(ShortcutId.UNDO).display() == FREE_COMBINATION

    def test_an_untouched_action_keeps_the_aliases_the_scheme_ships(self, draft: ShortcutDraft) -> None:
        scheme = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION)).scheme()

        assert scheme.shortcut(ShortcutId.REDO).aliases == (KeyCombination.parse("Ctrl+Shift+Z"),)

    def test_a_touched_action_answers_the_combination_it_was_given_alone(self, draft: ShortcutDraft) -> None:
        scheme = draft.assign(ShortcutId.ORDER_INSERT_FRAME, KeyCombination.parse("Ctrl+Alt+I")).scheme()

        assert scheme.shortcut(ShortcutId.ORDER_INSERT_FRAME).aliases == ()

    def test_two_actions_trade_the_combinations_they_held(self, draft: ShortcutDraft) -> None:
        """Every edit is read at once, so a swap arrives without either action holding both keys."""
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse("Ctrl+Y")).assign(
            ShortcutId.REDO,
            KeyCombination.parse("Ctrl+Z"),
        )
        scheme = edited.scheme()

        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Y")) is ShortcutId.UNDO
        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Z")) is ShortcutId.REDO

    def test_a_draft_on_the_shipped_keys_produces_the_scheme_it_opened_on(self, draft: ShortcutDraft) -> None:
        assert draft.scheme().bindings == draft.base.bindings

    def test_every_key_the_table_names_produces_a_scheme_that_resolves(self, draft: ShortcutDraft) -> None:
        """What a reader may assign is what the application then runs on, key for key."""
        assigned = {key: draft.assign(ShortcutId.UNDO, KeyCombination(key, CTRL)).scheme() for key in KEY_DISPLAY_NAMES}

        assert all(
            scheme.shortcut(ShortcutId.UNDO).combination == KeyCombination(key, CTRL)
            for key, scheme in assigned.items()
        )


class TestOverrides:
    def test_an_edit_stores_under_the_name_a_keybinding_file_writes(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION))

        assert edited.overrides() == {"Undo": FREE_COMBINATION}

    def test_an_edit_stores_the_combination_as_it_reads(self, draft: ShortcutDraft) -> None:
        """A stored preference is written the way the dialog shows it, whatever the reader typed."""
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse("shift+ctrl+alt+u"))

        assert edited.overrides() == {"Undo": "Ctrl+Alt+Shift+U"}

    def test_a_displaced_action_stores_as_unbound(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+S"))

        assert edited.overrides() == {"AboutDialog": "Ctrl+S", "SaveProject": None}

    def test_the_actions_the_reader_left_alone_store_nothing(self, draft: ShortcutDraft) -> None:
        """A preference states the actions the reader touched, so the rest follow the scheme."""
        edited = draft.assign(ShortcutId.UNDO, KeyCombination.parse(FREE_COMBINATION))

        assert set(edited.overrides()) == {"Undo"}

    def test_a_stored_draft_reopens_on_the_keys_it_stored(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+S"))

        reopened = ShortcutDraft.open(draft.base, edited.overrides())

        assert reopened.edits == edited.edits
        assert reopened.is_dirty is False
