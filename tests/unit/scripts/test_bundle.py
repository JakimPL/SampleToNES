from pathlib import Path
from typing import Callable, List, Sequence

import pytest

from bootstrap.cuda import GPU_CHOICES
from bootstrap.layout import (
    BUILD_ENVIRONMENT,
    BUILD_TOOLS,
    CUPY_PACKAGES,
    DISTRIBUTION,
    GPU_HOOK,
    GPU_PACKAGES,
    NOTICES,
    PYINSTALLER_HOOKS,
    RELEASE_HOOK,
)
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from bootstrap.platforms.windows import Windows
from bootstrap.project import BUILD_EXTRA, GPU_CUDA11_EXTRA, GPU_EXTRA, read_project
from tests.suite.bootstrap import PROJECT_NAME, RecordingRunner, write_project
from tests.suite.scripts import load_script

bundle = load_script("bundle.py")

CPU_RELEASE = bundle.BundleOptions(release=True, gpu_extra=None)
CPU_DEVELOPMENT = bundle.BundleOptions(release=False, gpu_extra=None)
GPU_DEVELOPMENT = bundle.BundleOptions(release=False, gpu_extra=GPU_EXTRA)


def _repository(tmp_path: Path) -> Path:
    for notice in NOTICES:
        (tmp_path / notice).write_text(notice)

    return write_project(tmp_path)


def _values(command: Sequence[str], flag: str) -> List[str]:
    return [command[index + 1] for index, argument in enumerate(command) if argument == flag]


class TestBundleOptions:
    def test_a_release_and_a_gpu_bundle_are_directories(self) -> None:
        assert CPU_RELEASE.directory
        assert GPU_DEVELOPMENT.directory
        assert not CPU_DEVELOPMENT.directory

    def test_gpu_support_follows_the_extra(self) -> None:
        assert GPU_DEVELOPMENT.gpu
        assert not CPU_RELEASE.gpu


class TestPyInstallerCommand:
    def test_a_release_is_a_directory_with_the_runtime_hook(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))

        command = bundle.pyinstaller_command(Path("python"), Linux().bundling(), project, CPU_RELEASE)

        assert command[:3] == ["python", "-m", "PyInstaller"]
        assert "--onedir" in command
        assert _values(command, "--runtime-hook") == [RELEASE_HOOK]
        assert command[-1] == project.entry_script

    def test_a_cpu_development_bundle_is_one_file_without_the_hook(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))

        command = bundle.pyinstaller_command(Path("python"), Linux().bundling(), project, CPU_DEVELOPMENT)

        assert "--onefile" in command
        assert "--runtime-hook" not in command

    def test_every_package_brings_its_data_and_the_build_tools_and_gpu_packages_stay_out(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))

        command = bundle.pyinstaller_command(Path("python"), Windows().bundling(), project, CPU_DEVELOPMENT)

        assert _values(command, "--collect-data") == list(project.packages)
        assert _values(command, "--exclude-module") == [*BUILD_TOOLS, *GPU_PACKAGES]
        assert _values(command, "--icon") == [Windows().bundling().icon]
        assert _values(command, "--name") == [project.name]

    def test_a_gpu_bundle_is_a_directory_collecting_cupy_through_the_hooks(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))

        command = bundle.pyinstaller_command(Path("python"), Linux().bundling(), project, GPU_DEVELOPMENT)

        assert "--onedir" in command
        assert _values(command, "--collect-all") == list(CUPY_PACKAGES)
        assert _values(command, "--additional-hooks-dir") == [PYINSTALLER_HOOKS]
        assert _values(command, "--runtime-hook") == [GPU_HOOK]
        assert _values(command, "--exclude-module") == list(BUILD_TOOLS)

    def test_a_gpu_release_carries_both_runtime_hooks(self, tmp_path: Path) -> None:
        project = read_project(_repository(tmp_path))
        options = bundle.BundleOptions(release=True, gpu_extra=GPU_EXTRA)

        command = bundle.pyinstaller_command(Path("python"), Linux().bundling(), project, options)

        assert _values(command, "--runtime-hook") == [GPU_HOOK, RELEASE_HOOK]


class TestExtras:
    def test_the_build_extra_is_always_installed_and_the_gpu_extra_beside_it(self) -> None:
        assert bundle.extras(CPU_DEVELOPMENT) == (BUILD_EXTRA,)
        assert bundle.extras(GPU_DEVELOPMENT) == (BUILD_EXTRA, GPU_EXTRA)
        assert bundle.extras(bundle.BundleOptions(release=False, gpu_extra=GPU_CUDA11_EXTRA)) == (
            BUILD_EXTRA,
            GPU_CUDA11_EXTRA,
        )


class TestSelfCheckCommand:
    def test_a_gpu_bundle_is_held_to_the_gpu_check(self) -> None:
        launcher = Path("bin", PROJECT_NAME, PROJECT_NAME)

        assert bundle.self_check_command(launcher, CPU_DEVELOPMENT) == (str(launcher), bundle.SELF_CHECK)
        assert bundle.self_check_command(launcher, GPU_DEVELOPMENT) == (
            str(launcher),
            bundle.SELF_CHECK,
            bundle.GPU_FLAG,
        )


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
        launcher = Linux().bundling().launcher(root / DISTRIBUTION, name=PROJECT_NAME, directory=True)
        runner = RecordingRunner({}, _leave_behind(root, launcher))

        built = bundle.build_bundle(root, Linux(), CPU_RELEASE, runner=runner, environment={})

        assert built == launcher
        assert runner.lines[0].endswith(BUILD_ENVIRONMENT)
        assert "pip install --upgrade pip" in runner.lines[1]
        assert f".[{BUILD_EXTRA}]" in runner.lines[2]
        assert "import pyaudio" in runner.lines[3]
        assert "import tkinter" in runner.lines[4]
        assert "PyInstaller" in runner.lines[5]
        assert runner.lines[6] == f"{launcher} {bundle.SELF_CHECK}"
        assert all((launcher.parent / notice).read_text() == notice for notice in NOTICES)

    def test_a_gpu_bundle_installs_the_extra_probes_cupy_and_lands_in_a_directory(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        launcher = Linux().bundling().launcher(root / DISTRIBUTION, name=PROJECT_NAME, directory=True)
        runner = RecordingRunner({}, _leave_behind(root, launcher))

        built = bundle.build_bundle(root, Linux(), GPU_DEVELOPMENT, runner=runner, environment={})

        assert built == launcher
        assert f".[{BUILD_EXTRA},{GPU_EXTRA}]" in runner.lines[2]
        assert "import cupy" in runner.lines[4]
        assert "import tkinter" in runner.lines[5]
        assert "PyInstaller" in runner.lines[6]
        assert runner.lines[7] == f"{launcher} {bundle.SELF_CHECK} {bundle.GPU_FLAG}"
        assert not any((launcher.parent / notice).exists() for notice in NOTICES)

    def test_a_bundle_pyinstaller_never_wrote_is_reported(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        elsewhere = tmp_path / "elsewhere" / PROJECT_NAME

        with pytest.raises(SystemExit, match="produced no executable"):
            bundle.build_bundle(
                root,
                Linux(),
                CPU_DEVELOPMENT,
                runner=RecordingRunner({}, _leave_behind(root, elsewhere)),
                environment={},
            )

    def test_a_launcher_failing_its_self_check_fails_the_build(self, tmp_path: Path) -> None:
        root = _repository(tmp_path)
        launcher = Linux().bundling().launcher(root / DISTRIBUTION, name=PROJECT_NAME, directory=False)

        with pytest.raises(SystemExit, match=bundle.SELF_CHECK):
            bundle.build_bundle(
                root,
                Linux(),
                CPU_DEVELOPMENT,
                runner=RecordingRunner({bundle.SELF_CHECK: 1}, _leave_behind(root, launcher)),
                environment={},
            )

    def test_a_system_without_bundles_is_told_to_run_from_source_before_anything_runs(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        with pytest.raises(SystemExit, match="make setup"):
            bundle.build_bundle(_repository(tmp_path), MacOS(), CPU_DEVELOPMENT, runner=runner, environment={})

        assert runner.lines == []


class TestMain:
    def test_a_gpu_choice_outside_the_extras_is_refused_before_anything_runs(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit) as exit_info:
            bundle.main(["--gpu", "1"])

        refusal = capsys.readouterr().err
        assert exit_info.value.code == 2
        assert all(choice in refusal for choice in GPU_CHOICES)
