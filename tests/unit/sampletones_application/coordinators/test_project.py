from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.project import ProjectCoordinator
from sampletones_shared.exceptions import NotAValidArchiveError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@pytest.fixture
def project_coordinator() -> ProjectCoordinator:
    return ProjectCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        layout=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
    )


class TestProjectRestoreSuccess:
    def test_loads_and_keeps_session_pointer(self, project_coordinator: ProjectCoordinator) -> None:
        path = Path("song.stp")

        project_coordinator.restore(path)

        project_coordinator._project_controller.load.assert_called_once_with(path)
        project_coordinator._session_manager.set_current_project.assert_not_called()


class TestProjectRestoreAbsorbsFailures(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        failure: Exception

    test_cases = [
        TestCase(label="invalid_archive", failure=NotAValidArchiveError("corrupt"), expected=None),
        TestCase(label="missing_file", failure=FileNotFoundError("gone"), expected=None),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_restore_clears_session_pointer(
        self,
        test_case: TestCase,
        project_coordinator: ProjectCoordinator,
    ) -> None:
        project_coordinator._project_controller.load.side_effect = test_case.failure

        project_coordinator.restore(Path("song.stp"))

        project_coordinator._session_manager.set_current_project.assert_called_once_with(test_case.expected)


class TestProjectRestorePropagatesUnexpected:
    def test_runtime_error_propagates(self, project_coordinator: ProjectCoordinator) -> None:
        project_coordinator._project_controller.load.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            project_coordinator.restore(Path("song.stp"))

        project_coordinator._session_manager.set_current_project.assert_not_called()
