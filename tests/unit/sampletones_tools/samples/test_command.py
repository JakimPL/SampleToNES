from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.samples.render import RenderedWave, RenderingError

RENDERER: Final[str] = "sampletones_tools.samples.render.render_directory"


class TestNsfRender:
    def test_every_wave_written_is_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        calls: List[Tuple[Path, float]] = []

        def render_directory(directory: Path, tail_seconds: float) -> List[RenderedWave]:
            calls.append((directory, tail_seconds))
            return [RenderedWave(source=directory / "a.nsf", destination=directory / "a.wav", seconds=1.5)]

        monkeypatch.setattr(RENDERER, render_directory)

        assert dispatch(COMMANDS, ["nsf", "render", "--directory", str(tmp_path)]) == 0
        assert calls == [(tmp_path, 0.5)]
        assert f"{tmp_path / 'a.wav'}  1.500 s" in capsys.readouterr().out

    def test_the_directory_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["nsf", "render"])

        assert leaving.value.code == 2

    def test_an_action_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["nsf"])

        assert leaving.value.code == 2

    def test_a_rendering_failure_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def fail(directory: Path, tail_seconds: float) -> List[RenderedWave]:
            raise RenderingError(f"ffmpeg is missing for {directory} at {tail_seconds}")

        monkeypatch.setattr(RENDERER, fail)

        with pytest.raises(SystemExit, match="ffmpeg is missing"):
            dispatch(COMMANDS, ["nsf", "render", "--directory", str(tmp_path)])
