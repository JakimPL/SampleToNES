from pathlib import Path

import pytest

from bootstrap.platforms import macos
from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from bootstrap.platforms.windows import Windows
from tests.suite.bootstrap import RecordingRunner
from tests.suite.scripts import load_script

system_dependencies = load_script("system_dependencies.py")


class TestInstallSystemPackages:
    def test_windows_has_nothing_to_install(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        runner = RecordingRunner({}, None)

        assert system_dependencies.install_system_packages(tmp_path, Windows(), runner=runner, environment={}) == 0
        assert runner.lines == []
        assert "Nothing to install" in capsys.readouterr().out

    def test_linux_runs_the_apt_commands_in_order(self, tmp_path: Path) -> None:
        runner = RecordingRunner({}, None)

        assert system_dependencies.install_system_packages(tmp_path, Linux(), runner=runner, environment={}) == 0
        assert runner.lines == [" ".join(command) for command in Linux().system_packages()]

    def test_macos_with_homebrew_installs_portaudio(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(macos.shutil, "which", lambda name: f"/opt/homebrew/bin/{name}")

        assert system_dependencies.install_system_packages(tmp_path, MacOS(), runner=runner, environment={}) == 0
        assert runner.lines == [" ".join(command) for command in MacOS().system_packages()]

    def test_macos_without_homebrew_is_refused(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runner = RecordingRunner({}, None)
        monkeypatch.setattr(macos.shutil, "which", lambda name: None)

        assert system_dependencies.install_system_packages(tmp_path, MacOS(), runner=runner, environment={}) == 1
        assert runner.lines == []
        assert "Homebrew" in capsys.readouterr().err

    def test_a_failing_install_stops_the_script(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="apt-get update"):
            system_dependencies.install_system_packages(
                tmp_path,
                Linux(),
                runner=RecordingRunner({"update": 100}, None),
                environment={},
            )
