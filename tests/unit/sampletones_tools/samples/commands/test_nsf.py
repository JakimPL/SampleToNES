from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.samples.emit import Emitter
from sampletones_tools.samples.nsf import write_samples
from sampletones_tools.samples.render import RenderedWave, RenderingError

RENDERER: Final[str] = "sampletones_tools.samples.render.render_directory"
EMITTER: Final[str] = "sampletones_tools.samples.emit.emit_samples"


class TestNsfSamples:
    def test_the_nsf_emitter_writes_into_the_output_and_every_file_is_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        calls: List[Tuple[Path, Emitter]] = []

        def emit_samples(output: Path, emitter: Emitter) -> List[Path]:
            calls.append((output, emitter))
            return [output / "kick.nsf", output / "song.nsf"]

        monkeypatch.setattr(EMITTER, emit_samples)

        assert dispatch(COMMANDS, ["nsf", "samples", "--output", str(tmp_path)]) == 0
        assert calls == [(tmp_path, write_samples)]
        assert capsys.readouterr().out.splitlines() == [
            f"Wrote {tmp_path / 'kick.nsf'}",
            f"Wrote {tmp_path / 'song.nsf'}",
        ]

    def test_the_output_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, ["nsf", "samples"])

        assert leaving.value.code == 2


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
