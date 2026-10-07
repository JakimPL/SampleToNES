import json
import subprocess
from pathlib import Path
from typing import Any, Final, List, Optional, Sequence

import pytest

from sampletones_tools.tracker_playback.paths import BITPHASE_TRACE_SCRIPT_PATH
from sampletones_tools.tracker_playback.targets.bitphase import engine
from sampletones_tools.tracker_playback.targets.bitphase.engine import (
    SOURCE_FILES,
    TSX_CLI,
    BitphaseEngine,
    BitphaseSource,
    EngineError,
)

NODE: Final[Path] = Path("node")
ONE_SILENT_TICK: Final[str] = json.dumps({"ticks": [{"frame": 0, "row": 0, "writes": []}]})


def _source(root: Path) -> BitphaseSource:
    for relative in SOURCE_FILES:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).touch()

    return BitphaseSource.located(root)


class TestBitphaseSource:
    def test_source_code_holding_every_file_the_trace_loads_is_located(self, tmp_path: Path) -> None:
        assert _source(tmp_path).root == tmp_path

    def test_source_code_without_its_packages_is_refused_naming_what_it_lacks(self, tmp_path: Path) -> None:
        _source(tmp_path)
        (tmp_path / TSX_CLI).unlink()

        with pytest.raises(EngineError, match="pnpm install") as refusal:
            BitphaseSource.located(tmp_path)

        assert str(TSX_CLI) in str(refusal.value)


class TestBitphaseEngine:
    def test_an_absent_node_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _source(tmp_path)
        monkeypatch.setattr(engine, "locate_program", lambda program: None)

        with pytest.raises(EngineError, match="node"):
            BitphaseEngine.located(tmp_path)

    def test_the_engine_takes_the_node_this_system_has(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        _source(tmp_path)
        monkeypatch.setattr(engine, "locate_program", lambda program: Path("/usr/bin") / program)

        located = BitphaseEngine.located(tmp_path)

        assert located.node == Path("/usr/bin") / "node"

    def test_the_trace_script_runs_through_the_source_codes_own_tsx(self, tmp_path: Path) -> None:
        played = BitphaseEngine(node=NODE, source=_source(tmp_path))
        document = tmp_path / "song.btp"
        output = tmp_path / "song.json"

        assert played.command(document, output) == [
            str(NODE),
            str(tmp_path / TSX_CLI),
            str(BITPHASE_TRACE_SCRIPT_PATH),
            str(tmp_path),
            str(document),
            str(output),
        ]

    def test_the_script_is_handed_absolute_paths(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        played = BitphaseEngine(node=NODE, source=_source(tmp_path / "bitphase"))
        monkeypatch.chdir(tmp_path)

        command = played.command(Path("run") / "song.btp", Path("run") / "song.json")

        assert [Path(argument) for argument in command[-2:]] == [
            tmp_path / "run" / "song.btp",
            tmp_path / "run" / "song.json",
        ]

    def test_a_trace_is_read_from_the_file_the_run_writes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        played = BitphaseEngine(node=NODE, source=_source(tmp_path))
        output = tmp_path / "song.json"
        runs: List[Optional[Path]] = []

        def run(command: Sequence[str], *, cwd: Path, **options: Any) -> None:
            runs.append(cwd)
            Path(command[-1]).write_text(ONE_SILENT_TICK, encoding="utf-8")

        monkeypatch.setattr(engine.subprocess, "run", run)

        trace = played.trace(tmp_path / "song.btp", output)

        assert runs == [tmp_path]
        assert trace.ticks == 1

    def test_a_failed_run_is_reported_with_what_it_printed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        played = BitphaseEngine(node=NODE, source=_source(tmp_path))

        def run(command: Sequence[str], **options: Any) -> None:
            raise subprocess.CalledProcessError(1, list(command), stderr="Song is empty")

        monkeypatch.setattr(engine.subprocess, "run", run)

        with pytest.raises(EngineError, match="Song is empty"):
            played.trace(tmp_path / "song.btp", tmp_path / "song.json")
