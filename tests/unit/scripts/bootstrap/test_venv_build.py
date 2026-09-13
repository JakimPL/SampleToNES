import sys
from pathlib import Path

from bootstrap.platforms.linux import Linux
from bootstrap.venv_build import BUILD_ENVIRONMENT, build_environment, install, interpreter
from tests.suite.bootstrap import RecordingRunner


class TestBuildEnvironment:
    def test_a_missing_environment_is_created_by_the_running_interpreter(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        directory = build_environment(tmp_path, runner=runner, environment={})

        assert directory == tmp_path / BUILD_ENVIRONMENT
        assert runner.lines == [f"{sys.executable} -m venv {directory}"]

    def test_an_existing_environment_is_kept(self, tmp_path: Path) -> None:
        (tmp_path / BUILD_ENVIRONMENT).mkdir()
        runner = RecordingRunner({}, None)

        build_environment(tmp_path, runner=runner, environment={})

        assert runner.lines == []


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


class TestInterpreter:
    def test_the_interpreter_lies_in_the_build_environment(self, tmp_path: Path) -> None:
        assert interpreter(tmp_path, Linux()) == tmp_path / BUILD_ENVIRONMENT / "bin" / "python"
