from pathlib import Path
from typing import Sequence

import pytest

from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

bundle = load_script("bundle.py")


class TestPyInstallerCommand:
    def test_a_release_is_a_directory_with_the_runtime_hook(self) -> None:
        options = bundle.BundleOptions(release=True, gpu=False)

        command = bundle.pyinstaller_command(Path("python"), Linux(), options)

        assert command[:3] == ["python", "-m", "PyInstaller"]
        assert "--onedir" in command
        assert "--runtime-hook" in command
        assert command[command.index("--runtime-hook") + 1] == bundle.RELEASE_HOOK
        assert command[-1] == bundle.ENTRY

    def test_a_development_bundle_is_one_file_without_the_hook(self) -> None:
        options = bundle.BundleOptions(release=False, gpu=False)

        command = bundle.pyinstaller_command(Path("python"), Linux(), options)

        assert "--onefile" in command
        assert "--runtime-hook" not in command

    def test_the_data_and_the_exclusions_ride_along(self) -> None:
        command = bundle.pyinstaller_command(Path("python"), Linux(), bundle.BundleOptions(release=False, gpu=False))

        data = [command[index + 1] for index, flag in enumerate(command) if flag == "--add-data"]
        assert data == [f"{source}:{destination}" for source, destination in bundle.DATA]
        assert command[command.index("--exclude-module") + 1] == "PIL"
        assert command[command.index("--icon") + 1] == Linux().icon


class TestExtras:
    def test_the_build_extra_is_always_installed_and_gpu_on_request(self) -> None:
        assert bundle.extras(bundle.BundleOptions(release=False, gpu=False)) == ("build",)
        assert bundle.extras(bundle.BundleOptions(release=False, gpu=True)) == ("build", "gpu")


class TestRemovePrevious:
    def test_a_previous_file_and_directory_are_removed(self, tmp_path: Path) -> None:
        (tmp_path / "sampletones").mkdir()
        (tmp_path / "sampletones.exe").write_text("")

        bundle.remove_previous(tmp_path)

        assert list(tmp_path.iterdir()) == []


def _repository(tmp_path: Path) -> Path:
    for notice in bundle.NOTICES:
        (tmp_path / notice).write_text(notice)

    return tmp_path


class TestBuildBundle:
    def test_a_release_runs_every_step_in_order_and_places_the_notices(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        platform = Linux()
        options = bundle.BundleOptions(release=True, gpu=False)
        launcher = platform.launcher(root / bundle.DISTRIBUTION, release=True)

        def leave_behind(command: Sequence[str]) -> None:
            if "venv" in command:
                platform.interpreter(root / ".venv-build").parent.mkdir(parents=True)
                platform.interpreter(root / ".venv-build").write_text("")

            if "PyInstaller" in command:
                launcher.parent.mkdir(parents=True)
                launcher.write_text("")

        runner = RecordingRunner({}, leave_behind)

        built = bundle.build_bundle(root, platform, options, runner=runner, environment={})

        assert built == launcher
        assert runner.lines[0].endswith(".venv-build")
        assert "pip install --upgrade pip" in runner.lines[1]
        assert ".[build]" in runner.lines[2]
        assert "import pyaudio" in runner.lines[3]
        assert "import tkinter" in runner.lines[4]
        assert runner.lines[5].endswith(bundle.ICONS_SCRIPT)
        assert "PyInstaller" in runner.lines[6]
        assert runner.lines[7] == f"{launcher} --self-check"
        assert all((launcher.parent / notice).read_text() == notice for notice in bundle.NOTICES)

    def test_a_bundle_pyinstaller_never_wrote_is_reported(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        platform = Linux()

        def leave_behind(command: Sequence[str]) -> None:
            if "venv" in command:
                platform.interpreter(root / ".venv-build").parent.mkdir(parents=True)
                platform.interpreter(root / ".venv-build").write_text("")

        with pytest.raises(SystemExit, match="produced no executable"):
            bundle.build_bundle(
                root,
                platform,
                bundle.BundleOptions(release=False, gpu=False),
                runner=RecordingRunner({}, leave_behind),
                environment={},
            )

    def test_a_launcher_failing_its_self_check_fails_the_build(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        platform = Linux()
        launcher = platform.launcher(root / bundle.DISTRIBUTION, release=False)

        def leave_behind(command: Sequence[str]) -> None:
            if "venv" in command:
                platform.interpreter(root / ".venv-build").parent.mkdir(parents=True)
                platform.interpreter(root / ".venv-build").write_text("")

            if "PyInstaller" in command:
                launcher.parent.mkdir(parents=True, exist_ok=True)
                launcher.write_text("")

        with pytest.raises(SystemExit, match="self-check"):
            bundle.build_bundle(
                root,
                platform,
                bundle.BundleOptions(release=False, gpu=False),
                runner=RecordingRunner({"--self-check": 1}, leave_behind),
                environment={},
            )


class TestMain:
    def test_a_system_without_bundles_is_told_to_run_from_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(bundle, "current_platform", MacOS)

        assert bundle.main([]) == 1
        assert "make setup" in capsys.readouterr().err
