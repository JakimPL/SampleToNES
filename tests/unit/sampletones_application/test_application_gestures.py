from dataclasses import dataclass
from typing import Callable, Final, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.application import Application
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.shell import ShortcutBindings
from sampletones_core.exports.format import ExportFormat
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.gates import HeldGate, held_gate

__all__ = ["held_gate"]

COLLABORATORS: Final[Tuple[str, ...]] = (
    "_project_coordinator",
    "_render_coordinator",
    "_sequencer_tab",
    "_config_coordinator",
    "_display_coordinator",
    "_keybindings_coordinator",
    "_shell",
)
OWN_GESTURES: Final[Tuple[str, ...]] = (
    "_add_current_reconstruction_to_sequencer",
    "_export_reconstruction_wav_dialog",
    "_export_reconstruction_instruments_dialog",
)


@pytest.fixture
def app(held_gate: HeldGate) -> Application:
    """An application whose collaborators are stand-ins, and whose open reconstruction has an edit on its way."""
    app = Application.__new__(Application)
    for name in COLLABORATORS:
        setattr(app, name, MagicMock())
    for name in OWN_GESTURES:
        setattr(app, name, MagicMock())
    app._reconstruction_coordinator = MagicMock(spec=ReconstructionCoordinator)
    app._reconstruction_coordinator.after_edits.side_effect = held_gate
    return app


@pytest.fixture
def bindings(app: Application) -> ShortcutBindings:
    return app._create_shortcut_bindings()


class TestAWholeDocumentGestureWaitsForTheEdits(BaseTestSuite):
    """A menu item or a key that reads or puts away a whole document runs once the edits before it land."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        press: Callable[[ShortcutBindings], None]
        gesture: Callable[[Application], MagicMock]

    test_cases = (
        TestCase(
            label="save_project",
            press=lambda bindings: bindings.save_project(),
            gesture=lambda app: app._project_coordinator.save,
        ),
        TestCase(
            label="save_project_as",
            press=lambda bindings: bindings.save_project_as(),
            gesture=lambda app: app._project_coordinator.save_as_dialog,
        ),
        TestCase(
            label="new_project",
            press=lambda bindings: bindings.new_project(),
            gesture=lambda app: app._project_coordinator.new_project_with_confirmation,
        ),
        TestCase(
            label="open_project",
            press=lambda bindings: bindings.open_project(),
            gesture=lambda app: app._project_coordinator.open_with_confirmation,
        ),
        TestCase(
            label="close_project",
            press=lambda bindings: bindings.close_project(),
            gesture=lambda app: app._project_coordinator.close_with_confirmation,
        ),
        TestCase(
            label="open_reconstruction",
            press=lambda bindings: bindings.open_reconstruction(),
            gesture=lambda app: app._reconstruction_coordinator.load_with_confirmation,
        ),
        TestCase(
            label="save_reconstruction",
            press=lambda bindings: bindings.save_reconstruction(),
            gesture=lambda app: app._reconstruction_coordinator.save,
        ),
        TestCase(
            label="save_reconstruction_as",
            press=lambda bindings: bindings.save_reconstruction_as(),
            gesture=lambda app: app._reconstruction_coordinator.save_as_dialog,
        ),
        TestCase(
            label="close_reconstruction",
            press=lambda bindings: bindings.close_reconstruction(),
            gesture=lambda app: app._reconstruction_coordinator.close_with_confirmation,
        ),
        TestCase(
            label="export_wav",
            press=lambda bindings: bindings.export_wav(),
            gesture=lambda app: app._export_reconstruction_wav_dialog,
        ),
        TestCase(
            label="add_to_sequencer",
            press=lambda bindings: bindings.add_reconstruction_to_sequencer(),
            gesture=lambda app: app._add_current_reconstruction_to_sequencer,
        ),
        TestCase(
            label="render_song",
            press=lambda bindings: bindings.render_song(),
            gesture=lambda app: app._render_coordinator.open,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_gesture_runs_once_the_edits_have_landed(
        self,
        test_case: TestCase,
        app: Application,
        bindings: ShortcutBindings,
        held_gate: HeldGate,
    ) -> None:
        test_case.press(bindings)
        test_case.gesture(app).assert_not_called()

        held_gate.release()

        test_case.gesture(app).assert_called_once_with()

    def test_an_export_keeps_the_format_it_was_asked_for(
        self,
        app: Application,
        bindings: ShortcutBindings,
        held_gate: HeldGate,
    ) -> None:
        bindings.export_instruments(ExportFormat.FAMITRACKER)
        held_gate.release()

        app._export_reconstruction_instruments_dialog.assert_called_once_with(ExportFormat.FAMITRACKER)

    def test_a_project_export_keeps_the_format_it_was_asked_for(
        self,
        app: Application,
        bindings: ShortcutBindings,
        held_gate: HeldGate,
    ) -> None:
        bindings.export_project(ExportFormat.BITPHASE)
        app._project_coordinator.export_project_dialog.assert_not_called()

        held_gate.release()

        app._project_coordinator.export_project_dialog.assert_called_once_with(ExportFormat.BITPHASE)

    def test_undo_leaves_the_wait_to_the_sequencer(
        self,
        app: Application,
        bindings: ShortcutBindings,
    ) -> None:
        """The sequencer's undo waits on the same edits, so the key reaches it as it stands."""
        assert bindings.undo == app._sequencer_tab.undo
        assert bindings.redo == app._sequencer_tab.redo
