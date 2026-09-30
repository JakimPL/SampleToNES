from pathlib import Path
from typing import Final, List, Sequence

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.project.project import Project
from sampletones_tools.tracker_playback.comparison import TraceComparison
from sampletones_tools.tracker_playback.corpus.build import CorpusProject
from sampletones_tools.tracker_playback.outcome import ProjectOutcome
from sampletones_tools.tracker_playback.report import MATCHES
from sampletones_tools.tracker_playback.session import PlaybackOutcome, PlaybackRun
from sampletones_tools.tracker_playback.targets.bitphase.engine import EngineError
from sampletones_tools.tracker_playback.targets.bitphase.target import BitphaseTarget
from tests.suite.playback import ReplayingTarget

COMMAND: Final[str] = "tracker-playback"
COMPARISON_CORPUS: Final[str] = "sampletones_tools.tracker_playback.corpus.build.comparison_corpus"
CHECK_CORPUS: Final[str] = "sampletones_tools.tracker_playback.session.check_corpus"
DEFAULT_OUTPUT: Final[str] = "sampletones_tools.tracker_playback.session.default_output"


def _matching_outcome(name: str) -> ProjectOutcome:
    return ProjectOutcome(
        project=CorpusProject(name=name, purpose="A tone.", project=Project.create()),
        comparison=TraceComparison(application_ticks=6, engine_ticks=6, timing=None, divergences=()),
        skipped_rows=0,
        truncation=None,
    )


@pytest.fixture(name="runs")
def runs_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    replaying_target: ReplayingTarget,
) -> List[PlaybackRun]:
    """The runs the command starts, each answered with one matching project, the target located as a replay."""
    runs: List[PlaybackRun] = []

    def check_corpus(projects: Sequence[CorpusProject], run: PlaybackRun) -> PlaybackOutcome:
        runs.append(run)
        return PlaybackOutcome(outcomes=(_matching_outcome("tone"),), report=tmp_path / "report.md")

    monkeypatch.setattr(BitphaseTarget, "located", classmethod(lambda cls, root: replaying_target))
    monkeypatch.setattr(COMPARISON_CORPUS, lambda corpus: [])
    monkeypatch.setattr(CHECK_CORPUS, check_corpus)
    return runs


class TestTrackerPlayback:
    def test_each_verdict_and_the_report_link_are_printed(
        self,
        runs: List[PlaybackRun],
        replaying_target: ReplayingTarget,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        arguments = [COMMAND, "bitphase", "--checkout", str(tmp_path), "-o", str(tmp_path / "run")]

        assert dispatch(COMMANDS, arguments) == 0
        (run,) = runs
        assert (run.target, run.output) == (replaying_target, tmp_path / "run")
        assert run.settings.examples_per_difference >= 1
        assert capsys.readouterr().out.splitlines() == [
            f"tone: {MATCHES}",
            f"Report: {(tmp_path / 'report.md').resolve().as_uri()}",
        ]

    def test_a_run_given_no_output_writes_where_the_default_names(
        self,
        runs: List[PlaybackRun],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(DEFAULT_OUTPUT, lambda: tmp_path / "stamped")

        assert dispatch(COMMANDS, [COMMAND, "bitphase", "--checkout", str(tmp_path)]) == 0
        assert [run.output for run in runs] == [tmp_path / "stamped"]

    def test_a_tracker_that_cannot_run_is_reported(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        def located(cls: type, root: Path) -> BitphaseTarget:
            raise EngineError("node is absent")

        monkeypatch.setattr(BitphaseTarget, "located", classmethod(located))

        with pytest.raises(SystemExit, match="node is absent"):
            dispatch(COMMANDS, [COMMAND, "bitphase", "--checkout", str(tmp_path)])

    def test_the_bitphase_checkout_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, [COMMAND, "bitphase"])

        assert leaving.value.code == 2

    def test_a_target_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, [COMMAND])

        assert leaving.value.code == 2
