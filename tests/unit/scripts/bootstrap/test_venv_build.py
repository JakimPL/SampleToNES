import sys
from pathlib import Path

from bootstrap.layout import BUILD_ENVIRONMENT
from bootstrap.platforms.linux import Linux
from bootstrap.venv_build import ensure_build_venv, install
from tests.suite.bootstrap import RecordingRunner


class TestEnsureBuildVenv:
    def test_a_missing_environment_is_created_by_the_running_interpreter(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        python = ensure_build_venv(tmp_path, Linux(), runner=runner, environment={})

        assert python == Linux().interpreter(tmp_path / BUILD_ENVIRONMENT)
        assert runner.lines == [f"{sys.executable} -m venv --clear {tmp_path / BUILD_ENVIRONMENT}"]

    def test_an_environment_with_its_interpreter_is_kept(self, tmp_path: Path) -> None:
        python = Linux().interpreter(tmp_path / BUILD_ENVIRONMENT)
        python.parent.mkdir(parents=True)
        python.write_text("")
        runner = RecordingRunner({}, None)

        assert ensure_build_venv(tmp_path, Linux(), runner=runner, environment={}) == python
        assert runner.lines == []

    def test_a_directory_an_interrupted_creation_left_is_created_again(self, tmp_path: Path) -> None:
        (tmp_path / BUILD_ENVIRONMENT).mkdir()
        runner = RecordingRunner({}, None)

        ensure_build_venv(tmp_path, Linux(), runner=runner, environment={})

        assert runner.lines == [f"{sys.executable} -m venv --clear {tmp_path / BUILD_ENVIRONMENT}"]


class TestInstall:
    def test_pip_is_upgraded_then_the_package_installed_with_its_extras(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)
        python = tmp_path / "python"

        install(
            tmp_path,
            python,
            extras=("build", "gpu"),
            runner=runner,
            environment={"PATH": "/usr/bin"},
        )

        assert runner.lines == [
            f"{python} -m pip install --upgrade pip",
            f"{python} -m pip install .[build,gpu]",
        ]

    def test_every_install_refuses_an_interpreter_outside_a_virtual_environment(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        install(tmp_path, tmp_path / "python", extras=("build",), runner=runner, environment={})

        assert all(recorded.environment["PIP_REQUIRE_VIRTUALENV"] == "1" for recorded in runner.commands)
