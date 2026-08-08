from pathlib import Path

import dearpygui.dearpygui as dpg
import pytest
from pydantic import ValidationError

from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, CTRL_SHIFT
from sampletones_application.utils.gui.shortcuts.catalog import DEFAULT_SCHEME_NAME
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.written import WrittenShortcut
from sampletones_core.paths import EXT_FILE_YAML
from tests.unit.sampletones_application.utils.gui.shortcuts.conftest import (
    PROBE_SCHEME_NAME,
    RebindScheme,
)

SHIPPED_FILE = KEYBINDINGS_DIRECTORY / f"{DEFAULT_SCHEME_NAME}{EXT_FILE_YAML}"

_PARTIAL_SCHEME_FILE = """
name: minimal
bindings:
  Play: {combination: "Space"}
"""


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
