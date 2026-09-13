import pytest

from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from bootstrap.platforms.windows import Windows
from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

system_dependencies = load_script("system_dependencies.py")


class TestMain:
    def test_windows_has_nothing_to_install(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(system_dependencies, "current_platform", Windows)

        assert system_dependencies.main([]) == 0
        assert "Nothing to install" in capsys.readouterr().out

    def test_linux_runs_the_apt_commands_in_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(system_dependencies, "current_platform", Linux)
        monkeypatch.setattr(system_dependencies, "run", runner)

        assert system_dependencies.main([]) == 0
        assert runner.lines[0] == "sudo apt-get update"
        assert runner.lines[1].startswith("sudo apt-get install -y")

    def test_macos_without_homebrew_is_refused(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(system_dependencies, "current_platform", MacOS)

        assert system_dependencies.main([]) == 1
        assert "Homebrew" in capsys.readouterr().err
