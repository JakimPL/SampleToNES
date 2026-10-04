from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.keyboard.combination import (
    KEY_LIST_JOINER,
    KeyCombination,
    display_combinations,
)
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
SECOND_FREE_COMBINATION = "Ctrl+Alt+N"
TABLE_COMBINATION = "Del"

UNNAMED_KEY = -1


def keys(*written: str) -> Tuple[KeyCombination, ...]:
    return tuple(KeyCombination.parse(combination) for combination in written)


def unbound_action(draft: ShortcutDraft) -> ShortcutId:
    """An action the scheme the draft opened on ships with no keys."""
    return next(shortcut_id for shortcut_id in ShortcutId if not draft.keys(shortcut_id))


@pytest.fixture
def draft(shipped: ShortcutScheme) -> ShortcutDraft:
    """A draft of the shipped scheme, opened on a session that stores no preference of its own."""
    return ShortcutDraft.open(shipped, {})


class TestOpen:
    def test_a_session_storing_nothing_opens_on_the_keys_the_scheme_ships(self, draft: ShortcutDraft) -> None:
        assert draft.keys(ShortcutId.UNDO) == keys("Ctrl+Z")

    def test_a_draft_opens_on_what_the_session_holds(self, shipped: ShortcutScheme) -> None:
        """A dialog asks whether the reader changed anything, which counts from the moment it opened."""
        assert ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"}).is_dirty is False

    def test_a_stored_override_opens_as_the_keys_its_action_answers(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"})

        assert draft.keys(ShortcutId.UNDO) == keys("Ctrl+Alt+U")

    def test_a_stored_override_reads_back_as_the_preference_it_came_from(self, shipped: ShortcutScheme) -> None:
        overrides: Dict[str, Optional[str]] = {"Undo": "Ctrl+Alt+U"}

        assert ShortcutDraft.open(shipped, overrides).overrides() == overrides

    def test_a_stored_override_stating_no_combination_opens_unbound(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": None})

        assert draft.keys(ShortcutId.UNDO) == ()

    def test_a_stored_override_listing_the_main_key_alone_opens_as_an_edit(self, shipped: ShortcutScheme) -> None:
        """An override lists every key of its action, so one naming the main key alone leaves out the rest."""
        main = shipped.shortcut(ShortcutId.ORDER_INSERT_FRAME).display()
        draft = ShortcutDraft.open(shipped, {"OrderInsertFrame": main})

        assert draft.overrides() == {"OrderInsertFrame": main}

    def test_a_stored_override_listing_every_shipped_key_opens_as_no_edit(self, shipped: ShortcutScheme) -> None:
        every = display_combinations(shipped.shortcut(ShortcutId.ORDER_INSERT_FRAME).combinations())
        draft = ShortcutDraft.open(shipped, {"OrderInsertFrame": every})

        assert draft.overrides() == {}

    def test_a_stored_single_key_opens_as_an_action_with_that_key_alone(self, shipped: ShortcutScheme) -> None:
        """A preference stored as one key per action reads the same way, as a list of one key."""
        draft = ShortcutDraft.open(shipped, {"Redo": FREE_COMBINATION})

        assert draft.keys(ShortcutId.REDO) == keys(FREE_COMBINATION)

    def test_a_stored_list_naming_a_key_twice_opens_and_stores_it_once(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Redo": f"{FREE_COMBINATION}{KEY_LIST_JOINER}{FREE_COMBINATION}"})

        assert (draft.keys(ShortcutId.REDO), draft.overrides()) == (
            keys(FREE_COMBINATION),
            {"Redo": FREE_COMBINATION},
        )

    def test_a_stored_list_opens_as_every_key_it_names(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Redo": f"{FREE_COMBINATION}, {SECOND_FREE_COMBINATION}"})

        assert draft.keys(ShortcutId.REDO) == keys(FREE_COMBINATION, SECOND_FREE_COMBINATION)

    def test_a_stored_list_naming_no_key_in_one_place_stays_behind_whole(self, shipped: ShortcutScheme) -> None:
        """An override that is unreadable in part costs its action alone, which keeps every shipped key."""
        draft = ShortcutDraft.open(shipped, {"Redo": f"{FREE_COMBINATION}, Ctrl+Nonsense", "Undo": "Ctrl+Alt+U"})

        assert draft.overrides() == {"Undo": "Ctrl+Alt+U"}
        assert draft.keys(ShortcutId.REDO) == shipped.shortcut(ShortcutId.REDO).combinations()

    def test_a_stored_override_this_build_carries_no_action_for_stays_behind(self, shipped: ShortcutScheme) -> None:
        """A preference outlives the build that stored it, so a stale entry costs only itself."""
        draft = ShortcutDraft.open(shipped, {"PlayLouder": "Ctrl+K", "Undo": "Ctrl+Alt+U"})

        assert draft.overrides() == {"Undo": "Ctrl+Alt+U"}

    def test_a_stored_override_its_category_already_answers_stays_behind(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"AboutDialog": "Ctrl+S"})

        assert draft.overrides() == {}


class TestKeys:
    def test_an_untouched_action_reads_every_key_the_scheme_gives_it(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        assert draft.keys(ShortcutId.REDO) == shipped.shortcut(ShortcutId.REDO).combinations()

    def test_an_assigned_action_reads_the_keys_the_reader_gave_it(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION, SECOND_FREE_COMBINATION))

        assert edited.keys(ShortcutId.UNDO) == keys(FREE_COMBINATION, SECOND_FREE_COMBINATION)

    def test_a_key_given_twice_counts_once(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION, FREE_COMBINATION))

        assert edited.keys(ShortcutId.UNDO) == keys(FREE_COMBINATION)

    def test_a_cleared_action_reads_as_unbound(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(ShortcutId.REDO)

        assert edited.keys(ShortcutId.REDO) == ()

    def test_an_action_the_scheme_leaves_unbound_reads_as_unbound(self, draft: ShortcutDraft) -> None:
        assert draft.keys(ShortcutId.ABOUT_DIALOG) == ()


class TestKeysLedBy:
    """A pressed key becomes the action's main key, and the keys it had follow it."""

    def test_a_new_key_leads_the_keys_the_action_had(self, draft: ShortcutDraft, shipped: ShortcutScheme) -> None:
        led = draft.keys_led_by(ShortcutId.REDO, KeyCombination.parse(FREE_COMBINATION))

        assert led == (KeyCombination.parse(FREE_COMBINATION), *shipped.shortcut(ShortcutId.REDO).combinations())

    def test_an_own_alias_moves_to_the_front_and_nothing_drops(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        redo = shipped.shortcut(ShortcutId.REDO)

        led = draft.keys_led_by(ShortcutId.REDO, redo.aliases[0])

        assert led[0] == redo.aliases[0]
        assert set(led) == set(redo.combinations())
        assert len(led) == len(redo.combinations())

    def test_an_own_alias_asks_no_one(self, draft: ShortcutDraft, shipped: ShortcutScheme) -> None:
        redo = shipped.shortcut(ShortcutId.REDO)

        assert draft.holders(ShortcutId.REDO, draft.keys_led_by(ShortcutId.REDO, redo.aliases[0])) == {}


class TestClaimant:
    def test_the_action_holding_a_combination_answers_for_it(self, draft: ShortcutDraft) -> None:
        claimant = draft.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+S"))

        assert claimant is ShortcutId.SAVE_PROJECT

    def test_an_alias_is_held_as_firmly_as_the_combination_it_extends(self, draft: ShortcutDraft) -> None:
        """An alias is a key its holder answers, so giving it away asks the holder as the main key does."""
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
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION))

        assert edited.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+Z")) is None

    def test_the_aliases_a_written_list_leaves_out_are_free(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.ORDER_INSERT_FRAME, keys("Ctrl+Alt+I"))

        assert edited.claimant(ShortcutId.ORDER_ADD_FRAME, KeyCombination.parse("NumPlus")) is None

    def test_the_aliases_a_pressed_key_leads_stay_held(self, draft: ShortcutDraft) -> None:
        """A pressed key joins the keys an action had, so its aliases still answer it."""
        led = draft.keys_led_by(ShortcutId.ORDER_INSERT_FRAME, KeyCombination.parse("Ctrl+Alt+I"))
        edited = draft.assign(ShortcutId.ORDER_INSERT_FRAME, led)

        assert edited.claimant(ShortcutId.ORDER_ADD_FRAME, KeyCombination.parse("NumPlus")) is (
            ShortcutId.ORDER_INSERT_FRAME
        )


class TestAssign(BaseTestSuite):
    """An assignment takes the combination from whichever action of the category holds it, and the holder
    keeps every other key it had.
    """

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
            shortcut_id=ShortcutId.VOICES_MOVE_VOICE_UP,
            written="F2",
            holder=ShortcutId.VOICES_RENAME_VOICE,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_action_that_held_the_combination_keeps_its_other_keys(
        self,
        test_case: TestCase,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        taken = KeyCombination.parse(test_case.written)
        edited = draft.assign(test_case.shortcut_id, (taken,))

        assert edited.keys(test_case.holder) == tuple(
            key for key in shipped.shortcut(test_case.holder).combinations() if key != taken
        )

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
        scheme = draft.assign(test_case.shortcut_id, (combination,)).scheme()

        assert scheme.claimant(test_case.shortcut_id.category, combination) is test_case.shortcut_id

    def test_an_assignment_leaves_the_draft_holding_keys_to_store(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION))

        assert edited.is_dirty is True

    def test_the_actions_an_assignment_leaves_alone_keep_their_keys(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION))

        assert edited.keys(ShortcutId.REDO) == shipped.shortcut(ShortcutId.REDO).combinations()

    def test_an_action_given_the_keys_it_already_answers_keeps_them(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys("Ctrl+Z"))

        assert edited.keys(ShortcutId.UNDO) == keys("Ctrl+Z")

    def test_an_action_given_the_keys_it_already_answers_records_nothing(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, draft.keys(ShortcutId.UNDO))

        assert (edited.is_dirty, edited.overrides()) == (False, {})

    def test_an_unbound_action_given_no_keys_records_nothing(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(unbound_action(draft), ())

        assert (edited.is_dirty, edited.overrides()) == (False, {})

    def test_an_action_given_back_its_shipped_keys_records_nothing(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION)).assign(
            ShortcutId.UNDO,
            draft.keys(ShortcutId.UNDO),
        )

        assert (edited.is_dirty, edited.overrides()) == (False, {})

    def test_a_list_taking_keys_from_two_actions_takes_each_from_its_holder(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        taken = (
            shipped.shortcut(ShortcutId.SAVE_PROJECT).combinations()[0],
            shipped.shortcut(ShortcutId.REDO).aliases[0],
        )

        edited = draft.assign(ShortcutId.ABOUT_DIALOG, taken)

        assert edited.holders(ShortcutId.ABOUT_DIALOG, taken) == {}
        assert draft.holders(ShortcutId.ABOUT_DIALOG, taken) == {
            taken[0]: ShortcutId.SAVE_PROJECT,
            taken[1]: ShortcutId.REDO,
        }
        assert edited.keys(ShortcutId.REDO) == (shipped.shortcut(ShortcutId.REDO).combinations()[0],)


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
            draft.assign(ShortcutId.UNDO, (test_case.combination,))

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_action_keeps_the_keys_it_had(self, test_case: TestCase, draft: ShortcutDraft) -> None:
        with pytest.raises(KeyError):
            draft.assign(ShortcutId.UNDO, (test_case.combination,))

        assert draft.keys(ShortcutId.UNDO) == keys("Ctrl+Z")
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
    def test_clearing_an_unbound_action_records_nothing(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(unbound_action(draft))

        assert (edited.is_dirty, edited.overrides()) == (False, {})

    def test_a_cleared_action_stores_as_unbound(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(ShortcutId.UNDO)

        assert edited.overrides() == {"Undo": None}

    def test_every_key_a_cleared_action_held_is_free_for_another(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        edited = draft.clear(ShortcutId.REDO)

        assert edited.holders(ShortcutId.ABOUT_DIALOG, shipped.shortcut(ShortcutId.REDO).combinations()) == {}

    def test_the_keys_a_cleared_action_held_are_free_for_another(self, draft: ShortcutDraft) -> None:
        edited = draft.clear(ShortcutId.UNDO)

        assert edited.claimant(ShortcutId.ABOUT_DIALOG, KeyCombination.parse("Ctrl+Z")) is None

    def test_the_scheme_a_cleared_action_produces_leaves_its_keys_unclaimed(self, draft: ShortcutDraft) -> None:
        scheme = draft.clear(ShortcutId.UNDO).scheme()

        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Z")) is None


class TestReset:
    def test_a_reset_draft_reads_the_keys_the_scheme_ships(self, shipped: ShortcutScheme) -> None:
        draft = ShortcutDraft.open(shipped, {"Undo": "Ctrl+Alt+U"}).reset()

        assert draft.keys(ShortcutId.UNDO) == keys("Ctrl+Z")

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
        scheme = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION, SECOND_FREE_COMBINATION)).scheme()

        assert scheme.shortcut(ShortcutId.UNDO).combinations() == keys(FREE_COMBINATION, SECOND_FREE_COMBINATION)

    def test_an_untouched_action_keeps_the_aliases_the_scheme_ships(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        scheme = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION)).scheme()

        assert scheme.shortcut(ShortcutId.REDO).aliases == shipped.shortcut(ShortcutId.REDO).aliases

    def test_a_pressed_key_leaves_the_action_answering_its_aliases_too(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        """A pressed key becomes the main key the menus print, and every key the action had still answers."""
        pressed = KeyCombination.parse("Ctrl+Alt+I")
        led = draft.keys_led_by(ShortcutId.ORDER_INSERT_FRAME, pressed)

        shortcut = draft.assign(ShortcutId.ORDER_INSERT_FRAME, led).scheme().shortcut(ShortcutId.ORDER_INSERT_FRAME)

        assert shortcut.combination == pressed
        assert shortcut.aliases == shipped.shortcut(ShortcutId.ORDER_INSERT_FRAME).combinations()

    def test_two_actions_trade_the_combinations_they_held(self, draft: ShortcutDraft) -> None:
        """Every edit is read at once, so a swap arrives without either action holding both keys."""
        edited = draft.assign(ShortcutId.UNDO, keys("Ctrl+Y")).assign(
            ShortcutId.REDO,
            keys("Ctrl+Z"),
        )
        scheme = edited.scheme()

        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Y")) is ShortcutId.UNDO
        assert scheme.claimant(ShortcutCategory.APPLICATION, KeyCombination.parse("Ctrl+Z")) is ShortcutId.REDO

    def test_a_draft_on_the_shipped_keys_produces_the_scheme_it_opened_on(self, draft: ShortcutDraft) -> None:
        assert draft.scheme().bindings == draft.base.bindings

    def test_every_key_the_table_names_produces_a_scheme_that_resolves(self, draft: ShortcutDraft) -> None:
        """What a reader may assign is what the application then runs on, key for key."""
        assigned = {
            key: draft.assign(ShortcutId.UNDO, (KeyCombination(key, CTRL),)).scheme() for key in KEY_DISPLAY_NAMES
        }

        assert all(
            scheme.shortcut(ShortcutId.UNDO).combination == KeyCombination(key, CTRL)
            for key, scheme in assigned.items()
        )


class TestOverrides:
    def test_an_edit_stores_under_the_name_a_keybinding_file_writes(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION))

        assert edited.overrides() == {"Undo": FREE_COMBINATION}

    def test_an_edit_stores_the_combination_as_it_reads(self, draft: ShortcutDraft) -> None:
        """A stored preference is written the way the dialog shows it, whatever the reader typed."""
        edited = draft.assign(ShortcutId.UNDO, keys("shift+ctrl+alt+u"))

        assert edited.overrides() == {"Undo": "Ctrl+Alt+Shift+U"}

    def test_a_displaced_action_stores_as_unbound(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.ABOUT_DIALOG, keys("Ctrl+S"))

        assert edited.overrides() == {"AboutDialog": "Ctrl+S", "SaveProject": None}

    def test_an_edit_stores_every_key_joined_by_commas(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION, SECOND_FREE_COMBINATION))

        assert edited.overrides() == {"Undo": f"{FREE_COMBINATION}, {SECOND_FREE_COMBINATION}"}

    def test_a_list_reopens_on_every_key_it_stored(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION, "Comma", SECOND_FREE_COMBINATION))

        reopened = ShortcutDraft.open(draft.base, edited.overrides())

        assert reopened.keys(ShortcutId.UNDO) == keys(FREE_COMBINATION, "Comma", SECOND_FREE_COMBINATION)

    def test_the_actions_the_reader_left_alone_store_nothing(self, draft: ShortcutDraft) -> None:
        """A preference states the actions the reader touched, so the rest follow the scheme."""
        edited = draft.assign(ShortcutId.UNDO, keys(FREE_COMBINATION))

        assert set(edited.overrides()) == {"Undo"}

    def test_a_stored_draft_reopens_on_the_keys_it_stored(self, draft: ShortcutDraft) -> None:
        edited = draft.assign(ShortcutId.ABOUT_DIALOG, keys("Ctrl+S"))

        reopened = ShortcutDraft.open(draft.base, edited.overrides())

        assert reopened.edits == edited.edits
        assert reopened.is_dirty is False


class TestEveryKey:
    def test_taking_an_alias_leaves_its_holder_answering_its_main_key(
        self,
        draft: ShortcutDraft,
        shipped: ShortcutScheme,
    ) -> None:
        redo = shipped.shortcut(ShortcutId.REDO)
        edited = draft.assign(ShortcutId.ABOUT_DIALOG, (redo.aliases[0],))

        assert edited.keys(ShortcutId.REDO) == (redo.combinations()[0],)

    def test_a_stored_list_reads_back_as_the_preference_it_came_from(self, shipped: ShortcutScheme) -> None:
        overrides: Dict[str, Optional[str]] = {"Redo": "Ctrl+Alt+R, Ctrl+Alt+Shift+R"}

        assert ShortcutDraft.open(shipped, overrides).overrides() == overrides
