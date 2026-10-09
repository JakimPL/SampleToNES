import pytest

from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from tests.suite.scripts import load_script

build_environment = load_script("build_environment.py")

PORTAUDIO_PREFIX = "/opt/homebrew/opt/portaudio"


class TestMain:
    def test_the_platform_s_flags_are_printed_one_per_line(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(build_environment, "current_platform", MacOS)
        monkeypatch.setattr(MacOS, "homebrew_prefix", staticmethod(lambda package: PORTAUDIO_PREFIX))
        monkeypatch.setattr(build_environment.running, "machine", lambda: "arm64")

        assert build_environment.main([]) == 0
        assert capsys.readouterr().out.splitlines() == list(MacOS().build_flags(machine="arm64"))

    def test_linux_prints_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(build_environment, "current_platform", Linux)

        assert build_environment.main([]) == 0
        assert capsys.readouterr().out == ""
