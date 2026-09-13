from pathlib import Path
from typing import Callable, Sequence

import pytest

from bootstrap.layout import BUILD_ENVIRONMENT, BUILD_TOOLS, DISTRIBUTION, NOTICES, RELEASE_HOOK
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from bootstrap.platforms.windows import Windows
from bootstrap.project import BUILD_EXTRA, GPU_EXTRA, read_project
from tests.suite.bootstrap import PROJECT_NAME, RecordingRunner, write_project
from tests.suite.scripts import load_script

bundle = load_script("bundle.py")


def _repository(tmp_path: Path) -> Path:
    for notice in NOTICES:
        (tmp_path / notice).write_text(notice)

    return write_project(tmp_path)


class TestPyInstallerCommand:
    def test_a_release_is_a_directory_with_the_runtime_hook(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))
        options = bundle.BundleOptions(release=True, gpu=False)

        command = bundle.pyinstaller_command(Path("python"), Linux().bundling(), project, options)

        assert command[:3] == ["python", "-m", "PyInstaller"]
        assert "--onedir" in command
        assert command[command.index("--runtime-hook") + 1] == RELEASE_HOOK
        assert command[-1] == project.entry_script

    def test_a_development_bundle_is_one_file_without_the_hook(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))

        command = bundle.pyinstaller_command(
            Path("python"),
            Linux().bundling(),
            project,
            bundle.BundleOptions(release=False, gpu=False),
        )

        assert "--onefile" in command
        assert "--runtime-hook" not in command

    def test_every_package_brings_its_data_and_the_build_tools_stay_out(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))

        command = bundle.pyinstaller_command(
            Path("python"),
            Windows().bundling(),
            project,
            bundle.BundleOptions(release=False, gpu=False),
        )

        collected = [command[index + 1] for index, flag in enumerate(command) if flag == "--collect-data"]
        excluded = [command[index + 1] for index, flag in enumerate(command) if flag == "--exclude-module"]
        assert collected == list(project.packages)
        assert excluded == list(BUILD_TOOLS)
        assert command[command.index("--icon") + 1] == Windows().bundling().icon
        assert command[command.index("--name") + 1] == project.name


class TestExtras:
    def test_the_build_extra_is_always_installed_and_gpu_on_request(self) -> None:
        assert bundle.extras(bundle.BundleOptions(release=False, gpu=False)) == (BUILD_EXTRA,)
        assert bundle.extras(bundle.BundleOptions(release=False, gpu=True)) == (BUILD_EXTRA, GPU_EXTRA)


class TestRemovePrevious:
    def test_a_previous_file_and_directory_are_removed(self, tmp_path: Path) -> None:
        (tmp_path / PROJECT_NAME).mkdir()
        (tmp_path / f"{PROJECT_NAME}.exe").write_text("")

        bundle.remove_previous(tmp_path, Windows().bundling(), PROJECT_NAME)

        assert list(tmp_path.iterdir()) == []


def _leave_behind(root: Path, launcher: Path) -> Callable[[Sequence[str]], None]:
    """What a build leaves on disk: the environment's interpreter, and the launcher where PyInstaller writes it."""

    def on_run(command: Sequence[str]) -> None:
        if "venv" in command:
            python = Linux().interpreter(root / BUILD_ENVIRONMENT)
            python.parent.mkdir(parents=True)
            python.write_text("")

        if "PyInstaller" in command:
            launcher.parent.mkdir(parents=True, exist_ok=True)
            launcher.write_text("")

    return on_run


class TestBuildBundle:
    def test_a_release_runs_every_step_in_order_and_places_the_notices(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        launcher = Linux().bundling().launcher(root / DISTRIBUTION, name=PROJECT_NAME, release=True)
        runner = RecordingRunner({}, _leave_behind(root, launcher))

        built = bundle.build_bundle(
            root, Linux(), bundle.BundleOptions(release=True, gpu=False), runner=runner, environment={}
        )

        assert built == launcher
        assert runner.lines[0].endswith(BUILD_ENVIRONMENT)
        assert "pip install --upgrade pip" in runner.lines[1]
        assert f".[{BUILD_EXTRA}]" in runner.lines[2]
        assert "import pyaudio" in runner.lines[3]
        assert "import tkinter" in runner.lines[4]
        assert "PyInstaller" in runner.lines[5]
        assert runner.lines[6] == f"{launcher} {bundle.SELF_CHECK}"
        assert all((launcher.parent / notice).read_text() == notice for notice in NOTICES)

    def test_a_bundle_pyinstaller_never_wrote_is_reported(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        elsewhere = tmp_path / "elsewhere" / PROJECT_NAME

        with pytest.raises(SystemExit, match="produced no executable"):
            bundle.build_bundle(
                root,
                Linux(),
                bundle.BundleOptions(release=False, gpu=False),
                runner=RecordingRunner({}, _leave_behind(root, elsewhere)),
                environment={},
            )

    def test_a_launcher_failing_its_self_check_fails_the_build(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        launcher = Linux().bundling().launcher(root / DISTRIBUTION, name=PROJECT_NAME, release=False)

        with pytest.raises(SystemExit, match=bundle.SELF_CHECK):
            bundle.build_bundle(
                root,
                Linux(),
                bundle.BundleOptions(release=False, gpu=False),
                runner=RecordingRunner({bundle.SELF_CHECK: 1}, _leave_behind(root, launcher)),
                environment={},
            )

    def test_a_system_without_bundles_is_told_to_run_from_source_before_anything_runs(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        with pytest.raises(SystemExit, match="make setup"):
            bundle.build_bundle(
                _repository(tmp_path),
                MacOS(),
                bundle.BundleOptions(release=False, gpu=False),
                runner=runner,
                environment={},
            )

        assert runner.lines == []
