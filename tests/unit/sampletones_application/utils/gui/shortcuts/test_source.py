from typing import List

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut
from tests.unit.sampletones_application.utils.gui.shortcuts.conftest import RebindScheme


class TestBindings:
    def test_the_source_reports_the_scheme_it_was_built_with(self, shipped: ShortcutScheme) -> None:
        assert ShortcutSource(shipped).scheme is shipped

    def test_an_action_resolves_its_keys_against_the_scheme_in_place(self, source: ShortcutSource) -> None:
        assert source.shortcut(ShortcutId.SAVE_PROJECT).display() == "Ctrl+S"

    def test_an_action_reads_under_the_combination_a_menu_prints(self, source: ShortcutSource) -> None:
        assert source.display(ShortcutId.UNDO) == "Ctrl+Z"


class TestActivate:
    def test_activating_another_scheme_replaces_the_one_in_place(
        self,
        source: ShortcutSource,
        rebound: RebindScheme,
    ) -> None:
        source.activate(rebound({ShortcutId.SAVE_PROJECT: WrittenShortcut(combination="Ctrl+Alt+K")}))

        assert source.display(ShortcutId.SAVE_PROJECT) == "Ctrl+Alt+K"

    def test_activating_announces_the_scheme_now_in_place(
        self,
        source: ShortcutSource,
        rebound: RebindScheme,
    ) -> None:
        activated: List[ShortcutScheme] = []
        source.on_bindings_changed = activated.append
        scheme = rebound({ShortcutId.SAVE_PROJECT: WrittenShortcut(combination="Ctrl+Alt+K")})

        source.activate(scheme)

        assert activated == [scheme]

    def test_activating_the_scheme_in_place_announces_nothing(
        self,
        source: ShortcutSource,
        shipped: ShortcutScheme,
    ) -> None:
        activated: List[ShortcutScheme] = []
        source.on_bindings_changed = activated.append

        source.activate(shipped)

        assert activated == []
