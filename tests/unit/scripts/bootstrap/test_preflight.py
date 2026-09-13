from pathlib import Path

import pytest

from bootstrap.platforms.linux import Linux
from bootstrap.preflight import can_import, check_build_interpreter
from tests.suite.bootstrap import RecordingRunner


@pytest.fixture
def python(tmp_path: Path) -> Path:
    interpreter = tmp_path / "python"
    interpreter.write_text("")
    return interpreter


class TestCanImport:
    def test_the_probe_is_quiet_and_answers_the_status(self, python: Path, tmp_path: Path) -> None:
        runner = RecordingRunner({"import tkinter": 1}, None)

        assert can_import(python, "pyaudio", runner=runner, cwd=tmp_path, environment={})
        assert not can_import(python, "tkinter", runner=runner, cwd=tmp_path, environment={})
        assert all(recorded.quiet for recorded in runner.commands)


class TestCheckBuildInterpreter:
    def test_a_missing_interpreter_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="build interpreter not found"):
            check_build_interpreter(
                tmp_path / "absent",
                Linux(),
                release=False,
                runner=RecordingRunner({}, None),
                cwd=tmp_path,
                environment={},
            )

    def test_an_interpreter_without_audio_playback_is_refused_with_the_platform_s_advice(
        self,
        python: Path,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(SystemExit, match="make system-deps"):
            check_build_interpreter(
                python,
                Linux(),
                release=False,
                runner=RecordingRunner({"import pyaudio": 1}, None),
                cwd=tmp_path,
                environment={},
            )

    def test_a_release_without_tk_is_refused(self, python: Path, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="tkinter"):
            check_build_interpreter(
                python,
                Linux(),
                release=True,
                runner=RecordingRunner({"import tkinter": 1}, None),
                cwd=tmp_path,
                environment={},
            )

    def test_a_development_bundle_without_tk_is_warned(
        self,
        python: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        check_build_interpreter(
            python,
            Linux(),
            release=False,
            runner=RecordingRunner({"import tkinter": 1}, None),
            cwd=tmp_path,
            environment={},
        )

        assert "WARNING" in capsys.readouterr().out

    def test_an_interpreter_carrying_both_passes(
        self,
        python: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        check_build_interpreter(
            python,
            Linux(),
            release=True,
            runner=RecordingRunner({}, None),
            cwd=tmp_path,
            environment={},
        )

        output = capsys.readouterr().out
        assert "pyaudio: available" in output
        assert "tkinter: available" in output
