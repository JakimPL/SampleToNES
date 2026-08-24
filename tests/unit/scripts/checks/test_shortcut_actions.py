from pathlib import Path
from typing import Final, List, Set

from sampletones_application.utils.gui.shortcuts.ids import (
    FAMILY_SHORTCUT_IDS,
    SHORTCUT_IDS_BY_NAME,
    ShortcutCategory,
    ShortcutId,
)
from sampletones_shared.meta.source.modules import SourceModule
from tests.suite.scripts import load_script
from tests.suite.source import parse_source

check_shortcut_actions = load_script("checks/shortcut_actions.py")

SCHEME: Final[Path] = Path("keybindings/default.yaml")
BOUND_ACTION: Final[ShortcutId] = ShortcutId.NEW_PROJECT
FAMILY_ACTION: Final[ShortcutId] = ShortcutId.EXPORT_PROJECT_FAMITRACKER
PANEL_ACTION: Final[ShortcutId] = ShortcutId.TRACKER_NEXT_ROW
DIALOG_ACTION: Final[ShortcutId] = ShortcutId.DIALOG_ACTIVATE

SHELL_SOURCE: Final[str] = """
def bind(bindings):
    return {
        ShortcutId.NEW_PROJECT: bindings.new_project,
        ShortcutId.OPEN_PROJECT: bindings.open_project,
    }
"""


def _module(source: str) -> SourceModule:
    return SourceModule(path=Path("module.py"), tree=parse_source(source))


def _kinds(findings: List[object]) -> Set[str]:
    return {finding.kind for finding in findings}  # type: ignore[attr-defined]


class TestWhereACallIsFound:
    """An action reaches its call either as a binding of its own or as a member of a family."""

    def test_a_binding_map_names_its_actions_as_keys(self) -> None:
        """The shell builds its map from the bindings it is handed, so the map is read as source."""
        assert check_shortcut_actions.mapping_keys(_module(SHELL_SOURCE)) == {"NEW_PROJECT", "OPEN_PROJECT"}

    def test_a_family_declares_the_actions_it_dispatches(self) -> None:
        """A family is declared rather than recognized, so what counts as one is never guessed."""
        assert FAMILY_ACTION in FAMILY_SHORTCUT_IDS

    def test_the_lookup_of_every_action_by_name_is_no_family(self) -> None:
        """`SHORTCUT_IDS_BY_NAME` answers with every action; reading it as a family would excuse
        every action from stating a call of its own."""
        assert set(SHORTCUT_IDS_BY_NAME.values()) - FAMILY_SHORTCUT_IDS


class TestUnansweredActions:
    def test_an_action_a_scheme_passes_over_is_reported(self) -> None:
        findings = check_shortcut_actions.unanswered_actions({SCHEME: set()}, (BOUND_ACTION,))

        assert [finding.location for finding in findings] == [str(SCHEME)]
        assert BOUND_ACTION.value in findings[0].message

    def test_an_action_every_scheme_states_passes(self) -> None:
        assert check_shortcut_actions.unanswered_actions({SCHEME: {BOUND_ACTION.value}}, (BOUND_ACTION,)) == []

    def test_each_scheme_is_held_to_the_whole_action_set(self) -> None:
        """A scheme no platform loads here falls behind silently, so every shipped one is read."""
        other = Path("keybindings/macos.yaml")
        schemes = {SCHEME: {BOUND_ACTION.value}, other: set()}

        findings = check_shortcut_actions.unanswered_actions(schemes, (BOUND_ACTION,))

        assert [finding.location for finding in findings] == [str(other)]


class TestUncalledActions:
    def test_an_application_action_with_no_call_is_reported(self) -> None:
        findings = check_shortcut_actions.uncalled_actions((BOUND_ACTION,), set())

        assert _kinds(findings) == {check_shortcut_actions.UNCALLED_ACTION}
        assert BOUND_ACTION.name in findings[0].message

    def test_an_action_a_binding_answers_passes(self) -> None:
        assert check_shortcut_actions.uncalled_actions((BOUND_ACTION,), {BOUND_ACTION.name}) == []

    def test_an_action_a_family_answers_passes(self) -> None:
        assert check_shortcut_actions.uncalled_actions((FAMILY_ACTION,), {FAMILY_ACTION.name}) == []

    def test_a_panel_action_needs_no_call_of_its_own(self) -> None:
        """A key scope acts on the press itself, so the shell's map answers for nothing there."""
        assert PANEL_ACTION.category is not ShortcutCategory.APPLICATION
        assert check_shortcut_actions.uncalled_actions((PANEL_ACTION,), set()) == []


class TestTheEditorsVocabulary:
    def test_a_rebindable_action_with_no_member_is_reported(self) -> None:
        findings = check_shortcut_actions.unnamed_actions((BOUND_ACTION,), set())

        assert _kinds(findings) == {check_shortcut_actions.UNNAMED_ACTION}

    def test_a_dialog_action_is_named_nowhere(self) -> None:
        """The dialog is operated by its own keys, so the editor leaves them as they are."""
        assert check_shortcut_actions.unnamed_actions((DIALOG_ACTION,), set()) == []

    def test_a_named_action_passes(self) -> None:
        assert check_shortcut_actions.unnamed_actions((BOUND_ACTION,), {BOUND_ACTION.name}) == []


class TestStaleEntries:
    def test_a_scheme_naming_a_dropped_action_is_reported(self) -> None:
        findings = check_shortcut_actions.stale_scheme_entries({SCHEME: {"RemovedLongAgo"}}, (BOUND_ACTION,))

        assert _kinds(findings) == {check_shortcut_actions.STALE_ENTRY}
        assert "RemovedLongAgo" in findings[0].message

    def test_a_scheme_naming_only_live_actions_passes(self) -> None:
        assert check_shortcut_actions.stale_scheme_entries({SCHEME: {BOUND_ACTION.value}}, (BOUND_ACTION,)) == []
