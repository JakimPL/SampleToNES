from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.skipped import MAX_REPORTED_ROWS
from sampletones_application.coordinators import project as project_module
from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.paths import LANG_EN
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.utils.callbacks.gates import Gate
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_core.exporters.skipped import NO_SKIPPED_ROWS, SkippedRow, SkipReason
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.format import ExportFormat
from sampletones_core.project import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_shared.exceptions import (
    IncompatibleProjectVersionError,
    IncorrectReconstructionDataError,
    InvalidProjectDataValuesError,
    MissingProjectDataFileError,
    NotAValidArchiveError,
    UnhandledProjectError,
)
from sampletones_shared.paths.extensions import EXT_FILE_MODULE
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.frames import held_frames
from tests.suite.questions import (
    StandingWindow,
    assert_the_answers_reach,
    dialogs_on_the_line,
    standing_window,
)
from tests.suite.silent_rows import MISSING_VOICE_ID, SILENT_CHANNEL

__all__ = ["held_frames", "standing_window"]

ORIGINAL_TITLE: Final[str] = "As saved"
EDITED_TITLE: Final[str] = "As edited"


@pytest.fixture
def project_coordinator() -> ProjectCoordinator:
    return ProjectCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        export_backends={},
        format_setups={},
        dialogs=dialogs_on_the_line(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
    )


class TestAProjectOpenedAtStart:
    """A project a run starts on stands for its file, as one opened by hand does.

    The session remembers the file, and Save writes there at once. A project the run never opened
    asks where to save it.
    """

    @pytest.fixture(name="save_dialog")
    def save_dialog_fixture(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        dialog = MagicMock(return_value=None)
        monkeypatch.setattr(project_module, "save_file_dialog", dialog)
        return dialog

    @pytest.fixture(name="saved_project")
    def saved_project_fixture(self, tmp_path: Path) -> Path:
        """A project file on disk, titled so a save can be told from the file as it was."""
        path = tmp_path / "song.stp"
        manager = ProjectManager()
        manager.current.info.title = ORIGINAL_TITLE
        manager.save(path)
        return path

    @pytest.fixture(name="starting")
    def starting_fixture(self, tmp_path: Path) -> ProjectCoordinator:
        """A coordinator over a real project manager, its session remembering nothing yet."""
        project_manager = ProjectManager()
        session_manager = MagicMock()
        session_manager.current_project = None
        session_manager.get_project_path.return_value = tmp_path
        return ProjectCoordinator(
            ProjectController(project_manager),
            project_manager,
            session_manager,
            MagicMock(),
            export_backends={},
            format_setups={},
            dialogs=dialogs_on_the_line(),
            language_manager=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
        )

    def test_the_session_remembers_its_file(self, starting: ProjectCoordinator, saved_project: Path) -> None:
        starting.load_project_safely(saved_project)

        starting._session_manager.set_current_project.assert_called_once_with(saved_project)

    def test_save_writes_its_file_without_asking(
        self,
        starting: ProjectCoordinator,
        saved_project: Path,
        save_dialog: MagicMock,
    ) -> None:
        starting.load_project_safely(saved_project)
        starting._project_controller.set_title(EDITED_TITLE)

        assert starting.save() is SaveOutcome.WRITTEN

        save_dialog.assert_not_called()
        assert ProjectContainer.load(saved_project).info.title == EDITED_TITLE

    def test_a_new_project_asks_where_to_save(
        self,
        starting: ProjectCoordinator,
        saved_project: Path,
        save_dialog: MagicMock,
    ) -> None:
        starting.load_project_safely(saved_project)
        starting.new_project()

        assert starting.save() is SaveOutcome.CALLED_OFF

        save_dialog.assert_called_once()
        starting._session_manager.set_current_project.assert_called_with(None)
        assert ProjectContainer.load(saved_project).info.title == ORIGINAL_TITLE


class TestProjectRestoreAbsorbsFailures(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        failure: Exception

    test_cases = (
        TestCase(
            label="invalid_archive",
            failure=NotAValidArchiveError("corrupt"),
            expected=None,
        ),
        TestCase(
            label="missing_file",
            failure=FileNotFoundError("gone"),
            expected=None,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_restore_clears_session_pointer(
        self,
        test_case: TestCase,
        project_coordinator: ProjectCoordinator,
    ) -> None:
        project_coordinator._project_controller.load.side_effect = test_case.failure

        project_coordinator.load_project_safely(Path("song.stp"))

        project_coordinator._session_manager.set_current_project.assert_called_once_with(test_case.expected)


class TestProjectRestorePropagatesUnexpected:
    def test_runtime_error_propagates(
        self,
        project_coordinator: ProjectCoordinator,
    ) -> None:
        project_coordinator._project_controller.load.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            project_coordinator.load_project_safely(Path("song.stp"))

        project_coordinator._session_manager.set_current_project.assert_not_called()


class TestProjectManualLoadSurfacesErrors(BaseTestSuite):
    """Opening a project by hand reports each concrete load failure through the error dialog, so a
    bad file is surfaced to the user instead of loading a broken project or crashing. The session
    pointer stays put on failure."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        failure: Exception

    test_cases = (
        TestCase(
            label="invalid_archive",
            failure=NotAValidArchiveError("corrupt"),
            expected=None,
        ),
        TestCase(
            label="incorrect_reconstruction",
            failure=IncorrectReconstructionDataError("bad"),
            expected=None,
        ),
        TestCase(
            label="invalid_values",
            failure=InvalidProjectDataValuesError("bad", ValueError("v")),
            expected=None,
        ),
        TestCase(
            label="missing_file",
            failure=MissingProjectDataFileError("missing"),
            expected=None,
        ),
        TestCase(
            label="incompatible_version",
            failure=IncompatibleProjectVersionError(
                "mismatch",
                expected_version="1.0",
                actual_version="9.0",
            ),
            expected=None,
        ),
        TestCase(label="unhandled", failure=UnhandledProjectError("unhandled"), expected=None),
        TestCase(label="os_error", failure=OSError("io"), expected=None),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_manual_load_shows_error_dialog(
        self,
        test_case: TestCase,
        project_coordinator: ProjectCoordinator,
    ) -> None:
        project_coordinator._project_controller.load.side_effect = test_case.failure

        project_coordinator._load(Path("song.stp"))

        project_coordinator._dialogs.show_error.assert_called_once_with(test_case.failure)
        project_coordinator._session_manager.set_current_project.assert_not_called()


class TestAFormatWithASetupOpensIt:
    """A format asking for its own choices opens its setup where the save dialog would, and every
    other format asks for the destination alone."""

    @pytest.fixture
    def setup(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def save_dialog(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        dialog = MagicMock(return_value=None)
        monkeypatch.setattr(project_module, "save_file_dialog", dialog)
        return dialog

    @pytest.fixture
    def coordinator(self, setup: MagicMock) -> ProjectCoordinator:
        backend = MagicMock()
        backend.extension.return_value = EXT_FILE_MODULE
        return ProjectCoordinator(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            export_backends={ExportFormat.FAMITRACKER: backend},
            format_setups={ExportFormat.NSF: setup},
            dialogs=dialogs_on_the_line(),
            language_manager=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
        )

    def test_a_format_with_a_setup_opens_it(
        self,
        coordinator: ProjectCoordinator,
        setup: MagicMock,
        save_dialog: MagicMock,
    ) -> None:
        coordinator.export_project_dialog(ExportFormat.NSF)

        setup.open_project.assert_called_once_with()
        save_dialog.assert_not_called()

    def test_a_format_asking_for_the_file_alone_opens_the_save_dialog(
        self,
        coordinator: ProjectCoordinator,
        setup: MagicMock,
        save_dialog: MagicMock,
    ) -> None:
        coordinator.export_project_dialog(ExportFormat.FAMITRACKER)

        save_dialog.assert_called_once()
        setup.open_project.assert_not_called()

    def test_a_closed_project_opens_nothing(
        self,
        coordinator: ProjectCoordinator,
        setup: MagicMock,
        save_dialog: MagicMock,
    ) -> None:
        coordinator._project_controller.is_open = False

        coordinator.export_project_dialog(ExportFormat.NSF)

        setup.open_project.assert_not_called()
        save_dialog.assert_not_called()


@pytest.fixture(name="coordinator")
def coordinator_fixture() -> ProjectCoordinator:
    """A coordinator reporting a finished export, in the shipped language."""
    project_manager = MagicMock()
    project_manager.current = Project.create(title="Demo", author="Tester", settings=ProjectSettings())
    return ProjectCoordinator(
        MagicMock(),
        project_manager,
        MagicMock(),
        MagicMock(),
        export_backends={},
        format_setups={},
        dialogs=dialogs_on_the_line(),
        language_manager=LanguageManager(LANG_EN),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
    )


def announced(coordinator: ProjectCoordinator) -> str:
    """The message the dialog announcing an export shows."""
    message: str = coordinator._dialogs.show_info.call_args.args[1]
    return message


class TestAWrittenProjectReportsTheRowsLeftSilent:
    """A project holding rows that name a voice with no instrument still exports, and the dialog
    announcing it lists those rows where the reader finds them in the tracker."""

    @staticmethod
    def _success(skipped_rows: tuple[SkippedRow, ...]) -> ExportSuccess:
        return ExportSuccess(
            kind=ExportKind.PROJECT,
            filepath=Path("song.ftm"),
            export_format=ExportFormat.FAMITRACKER,
            truncation=None,
            skipped_rows=skipped_rows,
        )

    @staticmethod
    def _row(index: int) -> SkippedRow:
        return SkippedRow(
            voice_id=MISSING_VOICE_ID,
            channel=SILENT_CHANNEL,
            order_position=3,
            row_index=index,
            reason=SkipReason.NO_INSTRUMENT,
        )

    def test_a_project_with_an_instrument_for_every_row_announces_the_export_alone(
        self,
        coordinator: ProjectCoordinator,
    ) -> None:
        coordinator._on_export_result(self._success(NO_SKIPPED_ROWS))

        assert announced(coordinator) == LanguageManager(LANG_EN)["global.dialog.message.project_exported_successfully"]

    def test_the_rows_follow_the_announcement(
        self,
        coordinator: ProjectCoordinator,
    ) -> None:
        coordinator._on_export_result(self._success((self._row(26),)))

        lines = announced(coordinator).splitlines()
        assert lines[0] == "FamiTracker module exported successfully."
        assert lines[-1].endswith("Frame 03, Pulse 1, row 1A: ..")

    def test_a_long_list_is_cut_where_the_dialog_can_hold_it(
        self,
        coordinator: ProjectCoordinator,
    ) -> None:
        left_out = 4
        rows = tuple(self._row(index) for index in range(MAX_REPORTED_ROWS + left_out))

        coordinator._on_export_result(self._success(rows))

        assert announced(coordinator).endswith(f"and {left_out} more")


class TestAWrittenProjectReportsTheInstrumentsShortened:
    """A format stores a bounded number of values per dimension, so the dialog announcing a
    project export says how many instruments it shortened."""

    @staticmethod
    def _success(
        truncation: Optional[EnvelopeTruncation],
        skipped_rows: tuple[SkippedRow, ...],
    ) -> ExportSuccess:
        return ExportSuccess(
            kind=ExportKind.PROJECT,
            filepath=Path("song.btp"),
            export_format=ExportFormat.BITPHASE,
            truncation=truncation,
            skipped_rows=skipped_rows,
        )

    def test_a_shortened_project_export_names_what_it_left_out(
        self,
        coordinator: ProjectCoordinator,
    ) -> None:
        truncation = EnvelopeTruncation(frames=512, source_frames=600, instruments=3)

        coordinator._on_export_result(self._success(truncation, NO_SKIPPED_ROWS))

        paragraphs = announced(coordinator).split("\n\n")
        assert paragraphs == [
            LanguageManager(LANG_EN)["global.dialog.message.bitphase_project_exported_successfully"],
            LanguageManager(LANG_EN)["global.dialog.template.export_truncated"].format(
                frames=truncation.frames,
                source_frames=truncation.source_frames,
                instruments=truncation.instruments,
            ),
        ]

    def test_a_whole_project_export_adds_no_notice(
        self,
        coordinator: ProjectCoordinator,
    ) -> None:
        coordinator._on_export_result(self._success(None, NO_SKIPPED_ROWS))

        assert (
            announced(coordinator)
            == LanguageManager(LANG_EN)["global.dialog.message.bitphase_project_exported_successfully"]
        )

    def test_the_instruments_shortened_follow_the_rows_left_silent(
        self,
        coordinator: ProjectCoordinator,
    ) -> None:
        silent = SkippedRow(
            voice_id=MISSING_VOICE_ID,
            channel=SILENT_CHANNEL,
            order_position=0,
            row_index=0,
            reason=SkipReason.NO_INSTRUMENT,
        )

        truncation = EnvelopeTruncation(frames=512, source_frames=600, instruments=1)

        coordinator._on_export_result(self._success(truncation, (silent,)))

        paragraphs = announced(coordinator).split("\n\n")
        assert paragraphs[1].startswith(LanguageManager(LANG_EN)["global.dialog.message.export_skipped_rows"])
        assert paragraphs[2] == LanguageManager(LANG_EN)["global.dialog.template.export_truncated"].format(
            frames=truncation.frames,
            source_frames=truncation.source_frames,
            instruments=truncation.instruments,
        )


class TestTheSaveAPromptWaitsOn:
    """A save prompt goes on, asks again or stands aside according to what the save came to."""

    @pytest.fixture(name="save_dialog")
    def save_dialog_fixture(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        dialog = MagicMock(return_value=None)
        monkeypatch.setattr(project_module, "save_file_dialog", dialog)
        return dialog

    @pytest.fixture(name="saving")
    def saving_fixture(
        self,
        project_coordinator: ProjectCoordinator,
        tmp_path: Path,
    ) -> ProjectCoordinator:
        project_coordinator._session_manager.get_project_path.return_value = tmp_path
        return project_coordinator

    def test_a_project_with_a_file_is_written_there(
        self,
        saving: ProjectCoordinator,
        tmp_path: Path,
    ) -> None:
        filepath = tmp_path / "song.stp"
        saving._project_manager.path = filepath

        assert saving.save() is SaveOutcome.WRITTEN
        saving._project_controller.save.assert_called_once_with(filepath)

    def test_a_file_dialog_closed_without_a_name_calls_the_save_off(
        self,
        saving: ProjectCoordinator,
        save_dialog: MagicMock,
    ) -> None:
        saving._project_manager.path = None

        assert saving.save() is SaveOutcome.CALLED_OFF
        saving._project_controller.save.assert_not_called()

    def test_a_name_chosen_in_the_file_dialog_is_written(
        self,
        saving: ProjectCoordinator,
        save_dialog: MagicMock,
        tmp_path: Path,
    ) -> None:
        filepath = tmp_path / "song.stp"
        save_dialog.return_value = filepath
        saving._project_manager.path = None

        assert saving.save() is SaveOutcome.WRITTEN
        saving._project_controller.save.assert_called_once_with(filepath)

    def test_a_write_that_fails_shows_its_error(
        self,
        saving: ProjectCoordinator,
        tmp_path: Path,
    ) -> None:
        failure = OSError("disk full")
        saving._project_manager.path = tmp_path / "song.stp"
        saving._project_controller.save.side_effect = failure

        assert saving.save() is SaveOutcome.FAILED
        assert saving._dialogs.show_error.call_args.args[0] is failure

    def test_a_save_asked_for_by_itself_says_it_landed(
        self,
        saving: ProjectCoordinator,
        tmp_path: Path,
    ) -> None:
        saving._project_manager.path = tmp_path / "song.stp"

        saving.save()

        saving._dialogs.show_info.assert_called_once()

    def test_a_save_a_prompt_asked_for_goes_on_without_a_word(
        self,
        saving: ProjectCoordinator,
        tmp_path: Path,
    ) -> None:
        """What the prompt guards opens next, so it opens alone."""
        filepath = tmp_path / "song.stp"
        saving._project_manager.path = filepath

        assert saving._write_project() is SaveOutcome.WRITTEN
        saving._project_controller.save.assert_called_once_with(filepath)
        saving._dialogs.show_info.assert_not_called()

    def test_every_save_prompt_waits_on_the_quiet_save(self, saving: ProjectCoordinator) -> None:
        saving._project_controller.is_open = True
        saving._project_controller.is_dirty = True

        saving.guard_close(MagicMock(), MagicMock())
        saving.guard_new(MagicMock(), MagicMock())

        for prompt in saving._dialogs.show_save_confirmation.call_args_list:
            assert prompt.kwargs["on_save"] == saving._write_project


class TestTheExitAsksAboutTheProject:
    """Exiting with unsaved project changes asks to save them first, the answer lets the exit go on, and
    Cancel turns it away."""

    def test_a_saved_project_lets_the_exit_go_on(self, project_coordinator: ProjectCoordinator) -> None:
        project_coordinator._project_controller.is_dirty = False
        proceed = MagicMock()
        decline = MagicMock()

        project_coordinator.guard_exit(proceed, decline)

        proceed.assert_called_once_with()
        decline.assert_not_called()
        project_coordinator._dialogs.show_save_confirmation.assert_not_called()

    def test_an_unsaved_project_asks_to_save_first(self, project_coordinator: ProjectCoordinator) -> None:
        project_coordinator._project_controller.is_dirty = True
        proceed = MagicMock()
        decline = MagicMock()

        project_coordinator.guard_exit(proceed, decline)

        proceed.assert_not_called()
        decline.assert_not_called()
        prompt = project_coordinator._dialogs.show_save_confirmation.call_args.kwargs
        assert prompt["on_save"] == project_coordinator._write_project
        assert_the_answers_reach(
            confirm=prompt["on_confirm"],
            cancel=prompt["on_cancel"],
            proceed=proceed,
            decline=decline,
        )


class TestReplacingOrClosingTheProject:
    """New, Open and Close ask before the open project goes, and Cancel turns the request away.

    An unsaved project is offered a save, an open project holding no changes is still asked about, and a
    request with no project open goes on at once, or, for Close, is turned away.
    """

    @pytest.fixture(name="proceed")
    def proceed_fixture(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture(name="decline")
    def decline_fixture(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.parametrize("guard", ["guard_new", "guard_open"])
    def test_no_project_open_goes_on_at_once(
        self,
        project_coordinator: ProjectCoordinator,
        proceed: MagicMock,
        decline: MagicMock,
        guard: str,
    ) -> None:
        project_coordinator._project_controller.is_open = False

        {"guard_new": project_coordinator.guard_new, "guard_open": project_coordinator.guard_open}[guard](
            proceed,
            decline,
        )

        proceed.assert_called_once_with()
        decline.assert_not_called()

    @pytest.mark.parametrize("guard", ["guard_new", "guard_open", "guard_close"])
    def test_an_unsaved_project_asks_and_cancel_turns_the_request_away(
        self,
        project_coordinator: ProjectCoordinator,
        proceed: MagicMock,
        decline: MagicMock,
        guard: str,
    ) -> None:
        project_coordinator._project_controller.is_open = True
        project_coordinator._project_controller.is_dirty = True

        {
            "guard_new": project_coordinator.guard_new,
            "guard_open": project_coordinator.guard_open,
            "guard_close": project_coordinator.guard_close,
        }[guard](proceed, decline)

        proceed.assert_not_called()
        prompt = project_coordinator._dialogs.show_save_confirmation.call_args.kwargs
        assert_the_answers_reach(
            confirm=prompt["on_confirm"],
            cancel=prompt["on_cancel"],
            proceed=proceed,
            decline=decline,
        )

    @pytest.mark.parametrize("guard", ["guard_new", "guard_open"])
    def test_a_saved_project_is_asked_about_and_cancel_turns_the_request_away(
        self,
        project_coordinator: ProjectCoordinator,
        proceed: MagicMock,
        decline: MagicMock,
        guard: str,
    ) -> None:
        project_coordinator._project_controller.is_open = True
        project_coordinator._project_controller.is_dirty = False

        {"guard_new": project_coordinator.guard_new, "guard_open": project_coordinator.guard_open}[guard](
            proceed,
            decline,
        )

        proceed.assert_not_called()
        prompt = project_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert_the_answers_reach(
            confirm=prompt["on_confirm"],
            cancel=prompt["on_cancel"],
            proceed=proceed,
            decline=decline,
        )

    def test_a_saved_project_closes_at_once(
        self,
        project_coordinator: ProjectCoordinator,
        proceed: MagicMock,
        decline: MagicMock,
    ) -> None:
        project_coordinator._project_controller.is_open = True
        project_coordinator._project_controller.is_dirty = False

        project_coordinator.guard_close(proceed, decline)

        proceed.assert_called_once_with()
        decline.assert_not_called()

    def test_closing_with_no_project_open_is_turned_away(
        self,
        project_coordinator: ProjectCoordinator,
        proceed: MagicMock,
        decline: MagicMock,
    ) -> None:
        project_coordinator._project_controller.is_open = False

        project_coordinator.guard_close(proceed, decline)

        proceed.assert_not_called()
        decline.assert_called_once_with()
        project_coordinator._dialogs.show_save_confirmation.assert_not_called()


def _close_the_project(controller: MagicMock) -> None:
    controller.is_open = False
    controller.is_dirty = False


def _save_the_project(controller: MagicMock) -> None:
    controller.is_dirty = False


class TestAQuestionAboutTheProjectWaitsForTheScreen(BaseTestSuite):
    """A guard asks about the open project once the screen is free for its question, reading the project then.

    A project another conversation closed or saved meanwhile lets the request through with no question.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        guard: Callable[[ProjectCoordinator], Gate]
        settle: Callable[[MagicMock], None]

    test_cases = (
        TestCase(label="new", guard=lambda coordinator: coordinator.guard_new, settle=_close_the_project),
        TestCase(label="open", guard=lambda coordinator: coordinator.guard_open, settle=_close_the_project),
        TestCase(label="close", guard=lambda coordinator: coordinator.guard_close, settle=_save_the_project),
        TestCase(label="exit", guard=lambda coordinator: coordinator.guard_exit, settle=_save_the_project),
    )

    @pytest.fixture(name="unsaved")
    def unsaved_fixture(self, project_coordinator: ProjectCoordinator) -> ProjectCoordinator:
        project_coordinator._project_controller.is_open = True
        project_coordinator._project_controller.is_dirty = True
        return project_coordinator

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_question_waits_while_another_window_stands(
        self,
        test_case: TestCase,
        unsaved: ProjectCoordinator,
        standing_window: StandingWindow,
    ) -> None:
        proceed = MagicMock()
        decline = MagicMock()

        test_case.guard(unsaved)(proceed, decline)

        unsaved._dialogs.show_save_confirmation.assert_not_called()
        proceed.assert_not_called()
        decline.assert_not_called()

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_question_asks_once_the_window_leaves(
        self,
        test_case: TestCase,
        unsaved: ProjectCoordinator,
        standing_window: StandingWindow,
    ) -> None:
        proceed = MagicMock()
        decline = MagicMock()
        test_case.guard(unsaved)(proceed, decline)

        standing_window.leave()

        prompt = unsaved._dialogs.show_save_confirmation.call_args.kwargs
        assert_the_answers_reach(
            confirm=prompt["on_confirm"],
            cancel=prompt["on_cancel"],
            proceed=proceed,
            decline=decline,
        )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_project_settled_meanwhile_goes_on_with_no_question(
        self,
        test_case: TestCase,
        unsaved: ProjectCoordinator,
        standing_window: StandingWindow,
    ) -> None:
        proceed = MagicMock()
        decline = MagicMock()
        test_case.guard(unsaved)(proceed, decline)

        test_case.settle(unsaved._project_controller)
        standing_window.leave()

        proceed.assert_called_once_with()
        decline.assert_not_called()
        unsaved._dialogs.show_save_confirmation.assert_not_called()
        unsaved._dialogs.show_confirmation.assert_not_called()

    def test_a_saved_project_lets_the_exit_go_on_while_another_window_stands(
        self,
        project_coordinator: ProjectCoordinator,
        standing_window: StandingWindow,
    ) -> None:
        """Leaving while a dialog stands goes on at once when there is nothing to ask about."""
        project_coordinator._project_controller.is_dirty = False
        proceed = MagicMock()

        project_coordinator.guard_exit(proceed, MagicMock())

        proceed.assert_called_once_with()
