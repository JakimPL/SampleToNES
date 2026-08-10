from dataclasses import fields
from unittest.mock import Mock

import pytest

from sampletones_application.constants.playback import FollowMode
from sampletones_application.shell import ApplicationShell, ShortcutBindings
from sampletones_application.utils.gui.shortcuts.ids import (
    FOLLOW_MODE_SHORTCUT_IDS,
    ShortcutCategory,
    ShortcutId,
)

APPLICATION_ACTIONS = frozenset(
    shortcut_id for shortcut_id in ShortcutId if shortcut_id.category is ShortcutCategory.APPLICATION
)


def _bindings() -> ShortcutBindings:
    """Bindings whose calls are all stand-ins, since the pairing is what the shell states."""
    return ShortcutBindings(**{field.name: Mock() for field in fields(ShortcutBindings)})


class TestShortcutCallbacks:
    def test_every_application_action_names_the_call_it_makes(self) -> None:
        """A menu asks the manager for any action it lists, which an unwired action answers with none."""
        assert frozenset(ApplicationShell._shortcut_callbacks(_bindings())) == APPLICATION_ACTIONS

    def test_an_export_action_carries_the_format_it_writes(self) -> None:
        bindings = _bindings()

        ApplicationShell._shortcut_callbacks(bindings)[ShortcutId.EXPORT_PROJECT_FAMITRACKER]()

        bindings.export_project.assert_called_once()

    def test_a_channel_action_carries_the_channel_it_switches(self) -> None:
        bindings = _bindings()

        ApplicationShell._shortcut_callbacks(bindings)[ShortcutId.TOGGLE_CHANNEL_NOISE]()

        bindings.toggle_channel.assert_called_once()

    @pytest.mark.parametrize("mode", list(FollowMode), ids=str)
    def test_a_follow_action_carries_the_reach_it_chooses(self, mode: FollowMode) -> None:
        bindings = _bindings()

        ApplicationShell._shortcut_callbacks(bindings)[FOLLOW_MODE_SHORTCUT_IDS[mode]]()

        bindings.set_follow_mode.assert_called_once_with(mode)
