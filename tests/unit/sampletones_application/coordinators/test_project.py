from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_shared.exceptions import (
    IncompatibleProjectVersionError,
    IncorrectReconstructionDataError,
    InvalidProjectDataValuesError,
    MissingProjectDataFileError,
    NotAValidArchiveError,
    UnhandledProjectError,
)
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
