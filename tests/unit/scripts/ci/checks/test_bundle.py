import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Sequence

import pytest

from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

check_bundle = load_script("ci/checks/bundle.py")

NOTICES = ("LICENSE", "THIRD-PARTY-NOTICES.md", "THIRD-PARTY-LICENSES.txt")


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    source = tmp_path / "bin" / "sampletones"
    source.mkdir(parents=True)
    for name in NOTICES:
        (source / name).write_text(name)

    return source


def _install_launcher(bundle: Path) -> Path:
    launcher: Path = check_bundle.launcher_path(
        bundle,
        system=check_bundle.platform.system(),
    )
    launcher.write_bytes(b"launcher")
    return launcher


def _stub_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int,
) -> List[Sequence[str]]:
    commands: List[Sequence[str]] = []

    def fake_run(
        command: Sequence[str],
        **_: Any,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=returncode,
        )

    monkeypatch.setattr(check_bundle.subprocess, "run", fake_run)
    return commands


class TestLauncherPath(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        system: str
        expected: str

    test_cases = (
        TestCase(
            label="windows_launcher_carries_an_extension",
            system="Windows",
            expected="sampletones.exe",
        ),
        TestCase(
            label="linux_launcher",
            system="Linux",
            expected="sampletones",
        ),
        TestCase(
            label="macos_launcher",
            system="Darwin",
            expected="sampletones",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_launcher_path(
        self,
        test_case: "TestLauncherPath.TestCase",
        tmp_path: Path,
    ) -> None:
        assert check_bundle.launcher_path(tmp_path, system=test_case.system).name == test_case.expected


class TestMissingNotices:
    def test_a_complete_bundle_lacks_nothing(self, bundle: Path) -> None:
        assert check_bundle.missing_notices(bundle) == []

    def test_every_absent_notice_is_reported(self, bundle: Path) -> None:
        (bundle / "LICENSE").unlink()
        (bundle / "THIRD-PARTY-LICENSES.txt").unlink()

        assert check_bundle.missing_notices(bundle) == [
            "LICENSE",
            "THIRD-PARTY-LICENSES.txt",
        ]

    def test_a_notice_directory_counts_as_absent(self, bundle: Path) -> None:
        (bundle / "LICENSE").unlink()
        (bundle / "LICENSE").mkdir()

        assert check_bundle.missing_notices(bundle) == ["LICENSE"]


class TestCarriedBuildTools:
    def test_an_application_bundle_holds_to_its_notices(self, bundle: Path) -> None:
        assert check_bundle.carried_build_tools(bundle) == []

    def test_a_build_tool_beside_the_application_is_reported(self, bundle: Path) -> None:
        (bundle / check_bundle.INTERNAL_DIRECTORY / "PIL").mkdir(parents=True)

        assert check_bundle.carried_build_tools(bundle) == ["PIL"]

    def test_a_build_tool_beside_the_launcher_is_reported(self, bundle: Path) -> None:
        (bundle / "PIL").mkdir()

        assert check_bundle.carried_build_tools(bundle) == ["PIL"]


class TestMain:
    def test_a_complete_bundle_passes(
        self,
        bundle: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        launcher = _install_launcher(bundle)
        commands = _stub_run(monkeypatch, returncode=0)

        assert check_bundle.main([str(bundle)]) == 0
        assert commands == [[str(launcher), "--version"]]

    def test_a_missing_notice_is_annotated_as_an_error(
        self,
        bundle: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _install_launcher(bundle)
        (bundle / "THIRD-PARTY-NOTICES.md").unlink()

        assert check_bundle.main([str(bundle)]) == 1

        output = capsys.readouterr().out
        assert output.startswith("::error::")
        assert "THIRD-PARTY-NOTICES.md" in output

    def test_bundled_build_tooling_is_annotated_as_an_error(
        self,
        bundle: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _install_launcher(bundle)
        (bundle / check_bundle.INTERNAL_DIRECTORY / "PIL").mkdir(parents=True)

        assert check_bundle.main([str(bundle)]) == 1

        output = capsys.readouterr().out
        assert output.startswith("::error::")
        assert "PIL" in output

    def test_a_missing_launcher_is_annotated_as_an_error(
        self,
        bundle: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert check_bundle.main([str(bundle)]) == 1
        assert capsys.readouterr().out.startswith("::error::")

    def test_a_launcher_that_fails_propagates_its_status(
        self,
        bundle: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _install_launcher(bundle)
        _stub_run(monkeypatch, returncode=3)

        assert check_bundle.main([str(bundle)]) == 3

    def test_the_launcher_runs_only_once_the_notices_are_present(
        self,
        bundle: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _install_launcher(bundle)
        (bundle / "LICENSE").unlink()
        commands = _stub_run(monkeypatch, returncode=0)

        check_bundle.main([str(bundle)])

        assert commands == []
