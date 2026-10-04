from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.application import Application
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.shell import ShortcutBindings
from sampletones_core.exports.format import ExportFormat
from sampletones_shared.types.callback import VoidCallback
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
    "_main_tab",
    "_shell",
)
OWN_GESTURES: Final[Tuple[str, ...]] = (
    "_add_current_reconstruction_to_sequencer",
    "_export_reconstruction_wav_dialog",
    "_export_reconstruction_instruments_dialog",
    "_exiting",
)
PROJECT_GUARDS: Final[Tuple[str, ...]] = ("guard_new", "guard_open", "guard_close")
RECONSTRUCTION_GUARDS: Final[Tuple[str, ...]] = ("guard_load", "guard_close")
FIRST_VOICE: Final[str] = "first-voice"
SECOND_VOICE: Final[str] = "second-voice"


def let_through(proceed: VoidCallback, _decline: VoidCallback) -> None:
    """A guard with nothing to ask about, which lets the request through at once."""
    proceed()


@pytest.fixture
def app(held_gate: HeldGate) -> Application:
    """An application whose collaborators are stand-ins, and whose open reconstruction has an edit on its way.

    Each document's guard has nothing to ask about, so a gesture reaches its action once the edits land.
    """
    app = Application.__new__(Application)
    for name in COLLABORATORS:
        setattr(app, name, MagicMock())
    for name in OWN_GESTURES:
        setattr(app, name, MagicMock())
    for name in PROJECT_GUARDS:
        getattr(app._project_coordinator, name).side_effect = let_through
    app._reconstruction_coordinator = MagicMock(spec=ReconstructionCoordinator)
    app._reconstruction_coordinator.after_edits.side_effect = held_gate
    for name in RECONSTRUCTION_GUARDS:
        getattr(app._reconstruction_coordinator, name).side_effect = let_through
    app._reconstruction_opening = app._reconstruction_opening_flight()
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
            gesture=lambda app: app._project_coordinator.new_project,
        ),
        TestCase(
            label="open_project",
            press=lambda bindings: bindings.open_project(),
            gesture=lambda app: app._project_coordinator.open_project,
        ),
        TestCase(
            label="close_project",
            press=lambda bindings: bindings.close_project(),
            gesture=lambda app: app._project_coordinator.close_project,
        ),
        TestCase(
            label="open_reconstruction",
            press=lambda bindings: bindings.open_reconstruction(),
            gesture=lambda app: app._reconstruction_coordinator.open,
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
            gesture=lambda app: app._reconstruction_coordinator.close,
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


class TestADocumentGestureAsksOnce(BaseTestSuite):
    """A gesture that replaces or closes a document, asked for twice while the edits before it are on
    their way, asks its question once, and the answer goes on with the request made last.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        press: Callable[[ShortcutBindings], None]
        guard: Callable[[Application], MagicMock]

    test_cases = (
        TestCase(
            label="new_project",
            press=lambda bindings: bindings.new_project(),
            guard=lambda app: app._project_coordinator.guard_new,
        ),
        TestCase(
            label="open_project",
            press=lambda bindings: bindings.open_project(),
            guard=lambda app: app._project_coordinator.guard_open,
        ),
        TestCase(
            label="close_project",
            press=lambda bindings: bindings.close_project(),
            guard=lambda app: app._project_coordinator.guard_close,
        ),
        TestCase(
            label="open_reconstruction",
            press=lambda bindings: bindings.open_reconstruction(),
            guard=lambda app: app._reconstruction_coordinator.guard_load,
        ),
        TestCase(
            label="close_reconstruction",
            press=lambda bindings: bindings.close_reconstruction(),
            guard=lambda app: app._reconstruction_coordinator.guard_close,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_two_presses_ask_once(
        self,
        test_case: TestCase,
        app: Application,
        bindings: ShortcutBindings,
        held_gate: HeldGate,
    ) -> None:
        test_case.guard(app).side_effect = None

        test_case.press(bindings)
        test_case.press(bindings)
        held_gate.release()

        test_case.guard(app).assert_called_once()

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_press_after_the_answer_asks_again(
        self,
        test_case: TestCase,
        app: Application,
        bindings: ShortcutBindings,
        held_gate: HeldGate,
    ) -> None:
        test_case.guard(app).side_effect = None
        test_case.press(bindings)
        held_gate.release()
        _, decline = test_case.guard(app).call_args.args

        decline()
        test_case.press(bindings)
        held_gate.release()

        assert test_case.guard(app).call_count == 2

    def test_a_browser_and_the_menu_share_one_opening(
        self,
        app: Application,
        bindings: ShortcutBindings,
        held_gate: HeldGate,
    ) -> None:
        """Opening a reconstruction asks once whichever door it was asked for through.

        The menu's Open, asked for last, is what the answer goes on with, so the reader picks a file.
        """
        guard = app._reconstruction_coordinator.guard_load
        guard.side_effect = None

        app._reconstruction_opening(Path("browsed.stn"))
        bindings.open_reconstruction()
        held_gate.release()

        guard.assert_called_once()
        proceed, _ = guard.call_args.args
        proceed()
        app._reconstruction_coordinator.open.assert_called_once_with()

    def test_two_browsed_files_open_the_second(
        self,
        app: Application,
        held_gate: HeldGate,
    ) -> None:
        guard = app._reconstruction_coordinator.guard_load
        guard.side_effect = None

        app._reconstruction_opening(Path("drums.stn"))
        app._reconstruction_opening(Path("bass.stn"))
        held_gate.release()

        guard.assert_called_once()
        proceed, _ = guard.call_args.args
        proceed()
        app._reconstruction_coordinator.open.assert_called_once_with(Path("bass.stn"))

    def test_editing_two_voices_opens_the_second(
        self,
        app: Application,
        held_gate: HeldGate,
    ) -> None:
        guard = app._reconstruction_coordinator.guard_edit_voice
        editing = app._voice_editing_flight()

        editing(FIRST_VOICE)
        editing(SECOND_VOICE)
        held_gate.release()

        guard.assert_called_once()
        proceed, _ = guard.call_args.args
        proceed()
        app._reconstruction_coordinator.open_project_voice.assert_called_once_with(SECOND_VOICE)


class TestLoadingWhatARunWroteAsksOnce:
    """The Converter's Load asks about the file it loads once, however often it is pressed meanwhile.

    The question speaks of the file the first press asked for, so the answer loads that file.
    """

    @pytest.fixture
    def guard(self, app: Application) -> MagicMock:
        guard = app._reconstruction_coordinator.guard_load_converted
        guard.side_effect = None
        return guard

    def test_two_presses_while_an_edit_is_on_its_way_ask_once(
        self,
        app: Application,
        guard: MagicMock,
        held_gate: HeldGate,
    ) -> None:
        loading = app._converted_loading_flight()

        loading(Path("written.stn"))
        loading(Path("written.stn"))
        held_gate.release()

        guard.assert_called_once()
        assert guard.call_args.args[0] == Path("written.stn")
        app._reconstruction_coordinator.load.assert_not_called()

    def test_a_second_file_asked_for_meanwhile_keeps_the_first(
        self,
        app: Application,
        guard: MagicMock,
        held_gate: HeldGate,
    ) -> None:
        loading = app._converted_loading_flight()

        loading(Path("written.stn"))
        loading(Path("rewritten.stn"))
        held_gate.release()

        guard.assert_called_once()
        filepath, proceed, _ = guard.call_args.args
        assert filepath == Path("written.stn")
        proceed()
        app._reconstruction_coordinator.load.assert_called_once_with(Path("written.stn"))

    def test_the_answer_loads_the_file_the_question_spoke_of(
        self,
        app: Application,
        guard: MagicMock,
        held_gate: HeldGate,
    ) -> None:
        loading = app._converted_loading_flight()
        loading(Path("written.stn"))
        held_gate.release()

        _, proceed, _ = guard.call_args.args
        proceed()

        app._reconstruction_coordinator.load.assert_called_once_with(Path("written.stn"))

    def test_a_press_after_cancel_asks_again(
        self,
        app: Application,
        guard: MagicMock,
        held_gate: HeldGate,
    ) -> None:
        loading = app._converted_loading_flight()
        loading(Path("written.stn"))
        held_gate.release()
        _, _, decline = guard.call_args.args

        decline()
        loading(Path("written.stn"))
        held_gate.release()

        assert guard.call_count == 2
        app._reconstruction_coordinator.load.assert_not_called()
