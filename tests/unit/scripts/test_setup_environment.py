from pathlib import Path
from typing import Final

import pytest

from bootstrap.cuda import GPU_CHOICES
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import ARCHFLAGS, MacOS
from bootstrap.project import DEVELOPMENT_GROUP, GPU_EXTRA
from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

setup_environment = load_script("setup_environment.py")

NAME: Final[str] = "sampletones"


class TestMain:
    def test_a_gpu_choice_outside_the_extras_is_refused_before_anything_runs(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit) as exit_info:
            setup_environment.main(["--gpu", "1"])

        refusal = capsys.readouterr().err
        assert exit_info.value.code == 2
        assert all(choice in refusal for choice in GPU_CHOICES)


class TestSetupCommands:
    def test_the_cpu_backend_synchronizes_and_installs_the_bare_package(self) -> None:
        commands = setup_environment.setup_commands(NAME, None)

        assert commands == [
            ["uv", "sync", "--group", DEVELOPMENT_GROUP],
            ["uv", "tool", "install", "--force", "--reinstall-package", NAME, "."],
        ]

    def test_a_gpu_extra_reaches_both_installs(self) -> None:
        commands = setup_environment.setup_commands(NAME, GPU_EXTRA)

        assert commands[0] == ["uv", "sync", "--group", DEVELOPMENT_GROUP, "--extra", GPU_EXTRA]
        assert commands[1] == ["uv", "tool", "install", "--force", "--reinstall-package", NAME, f".[{GPU_EXTRA}]"]


class TestSetUpEnvironment:
    def test_macos_runs_the_commands_on_its_native_architecture(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        setup_environment.set_up_environment(
            tmp_path,
            NAME,
            MacOS(),
            None,
            machine="arm64",
            runner=runner,
            environment={"PATH": "/usr/bin"},
        )

        assert runner.lines == [" ".join(command) for command in setup_environment.setup_commands(NAME, None)]
        assert all(recorded.environment[ARCHFLAGS] == "-arch arm64" for recorded in runner.commands)

    def test_linux_passes_the_variables_through(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        setup_environment.set_up_environment(
            tmp_path,
            NAME,
            Linux(),
            GPU_EXTRA,
            machine="x86_64",
            runner=runner,
            environment={"PATH": "/usr/bin"},
        )

        assert all(recorded.environment == {"PATH": "/usr/bin"} for recorded in runner.commands)
