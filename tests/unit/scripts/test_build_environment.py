import pytest

from bootstrap.platforms.linux import Linux
from bootstrap.platforms.macos import MacOS
from tests.suite.scripts import load_script

build_environment = load_script("build_environment.py")


class TestMain:
    def test_macos_prints_the_flags_one_per_line(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(build_environment, "current_platform", MacOS)
        monkeypatch.setattr(build_environment, "portaudio_prefix", lambda: "/opt/homebrew/opt/portaudio")
        monkeypatch.setattr(build_environment.running, "machine", lambda: "arm64")

        assert build_environment.main([]) == 0
        assert capsys.readouterr().out.splitlines() == [
            "CFLAGS=-I/opt/homebrew/opt/portaudio/include",
            "LDFLAGS=-L/opt/homebrew/opt/portaudio/lib",
            "ARCHFLAGS=-arch arm64",
        ]

    def test_linux_prints_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(build_environment, "current_platform", Linux)

        assert build_environment.main([]) == 0
        assert capsys.readouterr().out == ""
