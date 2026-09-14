from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators import project as project_module
from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_core.exports.format import ExportFormat
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


@pytest.fixture
def project_coordinator() -> ProjectCoordinator:
    return ProjectCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        export_backends={},
        format_setups={},
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
    )


class TestProjectRestoreSuccess:
    def test_loads_and_keeps_session_pointer(
        self,
        project_coordinator: ProjectCoordinator,
    ) -> None:
        path = Path("song.stp")

        project_coordinator.load_project_safely(path)

        project_coordinator._project_controller.load.assert_called_once_with(path)
        project_coordinator._session_manager.set_current_project.assert_not_called()


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
            dialogs=MagicMock(),
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
