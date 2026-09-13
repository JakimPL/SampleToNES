from unittest.mock import patch

import pytest

from sampletones.self_check import CHECKS, FAILURE_STATUS, SUCCESS_STATUS, run_self_check
from sampletones_shared.exceptions import FileDialogUnavailableError

RESOURCES_MODULE = "sampletones_application.ui.resources.resources"
SELECTION_MODULE = "sampletones_application.utils.file_dialogs.selection"


class TestRunSelfCheck:
    def test_source_checkout_passes(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = run_self_check()
        output = capsys.readouterr().out

        assert status == SUCCESS_STATUS
        for check in CHECKS:
            assert check.name in output

    def test_missing_resource_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{RESOURCES_MODULE}.get_font_path", side_effect=FileNotFoundError("Resource not found")):
            status = run_self_check()

        captured = capsys.readouterr()

        assert status == FAILURE_STATUS
        assert "resources" in captured.err
        assert "FileNotFoundError" in captured.err
        assert "file dialog backend" not in captured.out

    def test_unavailable_dialog_backend_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            f"{SELECTION_MODULE}.select_file_dialog_backend",
            side_effect=FileDialogUnavailableError("No file dialog backend is available."),
        ):
            status = run_self_check()

        assert status == FAILURE_STATUS
        assert "file dialog backend" in capsys.readouterr().err
