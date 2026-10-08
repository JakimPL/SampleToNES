import gzip
import json
from pathlib import Path
from typing import Any, Final, List, Sequence

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.settings import ProjectSettings
from sampletones_shared.paths.extensions import EXT_FILE_BITPHASE, EXT_FILE_JSON
from sampletones_tools.tracker_playback.targets.bitphase import engine
from sampletones_tools.tracker_playback.targets.bitphase.engine import (
    SOURCE_FILES,
    BitphaseEngine,
    BitphaseSource,
)
from sampletones_tools.tracker_playback.targets.bitphase.target import TITLE, BitphaseTarget
from tests.suite.performance import make_pulse_reconstruction, place_instrument, project_with_sample

NAME: Final[str] = "tone"


def _target(root: Path) -> BitphaseTarget:
    for relative in SOURCE_FILES:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).touch()

    return BitphaseTarget(engine=BitphaseEngine(node=Path("node"), source=BitphaseSource.located(root)))


class TestBitphaseTarget:
    def test_the_report_names_bitphase_and_the_source_code_that_plays(self, tmp_path: Path) -> None:
        target = _target(tmp_path)

        assert target.title == TITLE
        assert str(tmp_path) in target.player

    def test_the_target_takes_the_node_this_system_has(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        _target(tmp_path)
        monkeypatch.setattr(engine, "locate_program", lambda program: Path("bin") / program)

        located = BitphaseTarget.located(tmp_path)

        assert located.engine.source.root == tmp_path

    def test_a_project_is_exported_and_its_document_played_beside_the_trace(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        project, sample = project_with_sample(
            make_pulse_reconstruction(count=4),
            rows_per_pattern=1,
            settings=ProjectSettings(tempo=150, speed=6, nes_frequency=60),
        )
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=sample, volume=15)
        played: List[Sequence[str]] = []

        def run(command: Sequence[str], **options: Any) -> None:
            played.append(command)
            ticks = [{"frame": 0, "row": 0, "writes": []}]
            Path(command[-1]).write_text(json.dumps({"ticks": ticks}), encoding="utf-8")

        monkeypatch.setattr(engine.subprocess, "run", run)
        documents = tmp_path / "documents"
        documents.mkdir()

        playback = _target(tmp_path / "bitphase").play(project, documents, NAME)

        assert playback.document == documents / f"{NAME}{EXT_FILE_BITPHASE}"
        assert json.loads(gzip.decompress(playback.document.read_bytes()))
        assert [command[-2:] for command in played] == [
            [str(playback.document), str(documents / f"{NAME}{EXT_FILE_JSON}")],
        ]
        assert playback.trace.ticks == 1
        assert (playback.skipped_rows, playback.truncation) == ((), None)
