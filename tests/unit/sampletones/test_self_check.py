from pathlib import Path
from unittest.mock import patch

import pytest

from sampletones.self_check import (
    CHECKS,
    DOCUMENTATION_CHECK,
    FAILURE_STATUS,
    GPU_CHECK,
    SUCCESS_STATUS,
    checks_for,
    run_self_check,
)
from sampletones_shared import array
from sampletones_shared.array import CUPY_AVAILABLE
from sampletones_shared.documentation.site import DocumentationSite
from sampletones_shared.exceptions import FileDialogUnavailableError

RESOURCES_MODULE = "sampletones_application.ui.resources.resources"
SELECTION_MODULE = "sampletones_application.utils.file_dialogs.selection"
CUPY_REQUIRED_REASON = "the GPU check needs CuPy and an NVIDIA graphics card"


class TestRunSelfCheck:
    def test_source_checkout_passes(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = run_self_check(gpu=False, documentation=False)
        output = capsys.readouterr().out

        assert status == SUCCESS_STATUS
        for check in CHECKS:
            assert check.name in output

    def test_missing_resource_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(f"{RESOURCES_MODULE}.get_font_path", side_effect=FileNotFoundError("Resource not found")):
            status = run_self_check(gpu=False, documentation=False)

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
            status = run_self_check(gpu=False, documentation=False)

        assert status == FAILURE_STATUS
        assert "file dialog backend" in capsys.readouterr().err


class TestChecksFor:
    def test_a_cpu_build_runs_the_startup_checks_alone(self) -> None:
        assert checks_for(gpu=False, documentation=False) == CHECKS

    def test_a_gpu_build_adds_the_gpu_check_last(self) -> None:
        assert checks_for(gpu=True, documentation=False) == (*CHECKS, GPU_CHECK)

    def test_an_installed_build_adds_the_documentation_check(self) -> None:
        assert checks_for(gpu=False, documentation=True) == (*CHECKS, DOCUMENTATION_CHECK)

    def test_the_gpu_check_stays_last(self) -> None:
        assert checks_for(gpu=True, documentation=True) == (*CHECKS, DOCUMENTATION_CHECK, GPU_CHECK)


class TestGpuCheck:
    def test_the_inventory_names_the_array_backend(self, capsys: pytest.CaptureFixture[str]) -> None:
        run_self_check(gpu=False, documentation=False)

        assert "array backend" in capsys.readouterr().out

    def test_a_gpu_build_computing_on_the_cpu_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(array, "CUPY_AVAILABLE", False)

        status = run_self_check(gpu=True, documentation=False)

        captured = capsys.readouterr()
        assert status == FAILURE_STATUS
        assert GPU_CHECK.name in captured.err
        assert "GPUBackendError" in captured.err

    @pytest.mark.skipif(not CUPY_AVAILABLE, reason=CUPY_REQUIRED_REASON)
    def test_a_gpu_build_computing_on_the_card_passes(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = run_self_check(gpu=True, documentation=False)

        output = capsys.readouterr().out
        assert status == SUCCESS_STATUS
        assert GPU_CHECK.name in output
        assert f"{len(CHECKS) + 1} checks passed" in output


@pytest.fixture(name="shipped")
def shipped_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DocumentationSite:
    """A sealed site standing where the build's documentation is read from."""
    site = DocumentationSite(tmp_path / "documentation")
    site.directory.mkdir()
    site.index.write_text("<p>index</p>", encoding="utf-8")
    site.write_stamp()
    monkeypatch.setattr(DocumentationSite, "shipped", lambda: site)
    return site


class TestDocumentationCheck:
    def test_a_sealed_site_passes(self, shipped: DocumentationSite, capsys: pytest.CaptureFixture[str]) -> None:
        status = run_self_check(gpu=False, documentation=True)

        assert status == SUCCESS_STATUS
        assert f"{DOCUMENTATION_CHECK.name}: 1 pages, stamp {shipped.read_stamp()}" in capsys.readouterr().out

    def test_a_page_changed_after_sealing_fails(
        self,
        shipped: DocumentationSite,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shipped.index.write_text("<p>changed</p>", encoding="utf-8")

        status = run_self_check(gpu=False, documentation=True)

        assert status == FAILURE_STATUS
        assert "differs from its stamp" in capsys.readouterr().err

    def test_a_build_without_pages_fails(self, shipped: DocumentationSite, capsys: pytest.CaptureFixture[str]) -> None:
        shipped.stamp_path.unlink()

        status = run_self_check(gpu=False, documentation=True)

        assert status == FAILURE_STATUS
        assert "DocumentationUnavailableError" in capsys.readouterr().err
