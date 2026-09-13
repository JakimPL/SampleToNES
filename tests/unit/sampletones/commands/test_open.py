import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from tests.suite.commands import RecordedApplication
from tests.suite.files import empty_file

LAUNCHER = "sampletones.run.run_application"
ENGINE_MODULES: Final[Tuple[str, ...]] = ("numpy", "scipy", "sampletones_core.reconstructions")
REFUSAL_PROBE: Final[str] = """
import json, sys
from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
try:
    dispatch(COMMANDS, ["open", sys.argv[1]])
except SystemExit:
    print(json.dumps(sorted(sys.modules)))
"""


def _file(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b"")
    return path


class TestOpen:
    @pytest.mark.parametrize(
        ("name", "field"),
        [("song.stp", "project"), ("song.stn", "reconstruction"), ("library.ins", "library")],
    )
    def test_a_file_is_loaded_by_its_kind(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        name: str,
        field: str,
    ) -> None:
        application = RecordedApplication()
        monkeypatch.setattr(LAUNCHER, application)
        path = _file(tmp_path, name)

        assert dispatch(COMMANDS, ["open", str(path), "--config", "custom.json"]) == 0
        start = application.starts[0]
        assert start[field] == path
        assert start["config"] == Path("custom.json")
        assert [key for key, value in start.items() if value is None] == [
            key for key in ("library", "reconstruction", "project") if key != field
        ]

    def test_a_recording_is_pointed_at_convert(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        application = RecordedApplication()
        monkeypatch.setattr(LAUNCHER, application)
        path = _file(tmp_path, "song.wav")

        with pytest.raises(SystemExit, match=re.escape(f"sampletones convert {path}")):
            dispatch(COMMANDS, ["open", str(path)])

        assert application.starts == []

    def test_a_file_of_another_kind_is_refused(self, tmp_path: Path) -> None:
        path = _file(tmp_path, "notes.txt")

        with pytest.raises(SystemExit, match="neither"):
            dispatch(COMMANDS, ["open", str(path)])

    def test_a_missing_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="No file at"):
            dispatch(COMMANDS, ["open", str(tmp_path / "absent.stp")])


class TestRefusingARecording:
    """Pointing a recording at convert is a check on its name, which a fresh interpreter makes without the engine."""

    def test_the_refusal_loads_no_engine(self, tmp_path: Path) -> None:
        completed = subprocess.run(
            [sys.executable, "-c", REFUSAL_PROBE, str(empty_file(tmp_path, "song.wav"))],
            check=True,
            capture_output=True,
            text=True,
        )

        modules: List[str] = json.loads(completed.stdout)
        assert set(modules) & set(ENGINE_MODULES) == set()
