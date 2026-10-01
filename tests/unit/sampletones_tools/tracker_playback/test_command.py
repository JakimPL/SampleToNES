from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, List, Sequence

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_tools.tracker_playback.comparison import TraceComparison
from sampletones_tools.tracker_playback.outcome import ProjectOutcome
from sampletones_tools.tracker_playback.projects import CheckedProject
from sampletones_tools.tracker_playback.report import MATCHES
from sampletones_tools.tracker_playback.session import PlaybackOutcome, PlaybackRun
from sampletones_tools.tracker_playback.targets.bitphase.engine import EngineError
from sampletones_tools.tracker_playback.targets.bitphase.target import BitphaseTarget
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.target import FamiTrackerTarget
from tests.suite.playback import ReplayingTarget

COMMAND: Final[str] = "tracker-playback"
COMPARISON_CORPUS: Final[str] = "sampletones_tools.tracker_playback.corpus.build.comparison_corpus"
CHECK_PROJECTS: Final[str] = "sampletones_tools.tracker_playback.session.check_projects"
DEFAULT_OUTPUT: Final[str] = "sampletones_tools.tracker_playback.session.default_output"
CORPUS_PROJECT: Final[str] = "corpus-tone"


def _matching_outcome(name: str) -> ProjectOutcome:
    return ProjectOutcome(
        project=CheckedProject(name=name, purpose="A tone.", project=Project.create()),
        comparison=TraceComparison(application_ticks=6, engine_ticks=6, timing=None, divergences=()),
        skipped_rows=0,
        truncation=None,
    )


@dataclass
class StartedRuns:
    """What the command started: each run, and the names of the projects it was handed."""

    runs: List[PlaybackRun] = field(default_factory=list)
    projects: List[List[str]] = field(default_factory=list)


@pytest.fixture(name="started")
def started_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    replaying_target: ReplayingTarget,
) -> StartedRuns:
    """The runs the command starts, each answered with one matching project, the target located as a replay.

    The corpus is a single project named ``CORPUS_PROJECT``.
    """
    started = StartedRuns()

    def check_projects(projects: Sequence[CheckedProject], run: PlaybackRun) -> PlaybackOutcome:
        started.runs.append(run)
        started.projects.append([project.name for project in projects])
        return PlaybackOutcome(outcomes=(_matching_outcome("tone"),), report=tmp_path / "report.md")

    monkeypatch.setattr(BitphaseTarget, "located", classmethod(lambda cls, root: replaying_target))
    monkeypatch.setattr(COMPARISON_CORPUS, lambda corpus: [_matching_outcome(CORPUS_PROJECT).project])
    monkeypatch.setattr(CHECK_PROJECTS, check_projects)
    return started


class TestTrackerPlayback:
    def test_each_verdict_and_the_report_link_are_printed(
        self,
        started: StartedRuns,
        replaying_target: ReplayingTarget,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        arguments = [COMMAND, "bitphase", "--checkout", str(tmp_path), "-o", str(tmp_path / "run")]

        assert dispatch(COMMANDS, arguments) == 0
        (run,) = started.runs
        assert (run.target, run.output) == (replaying_target, tmp_path / "run")
        assert run.settings.examples_per_difference >= 1
        assert capsys.readouterr().out.splitlines() == [
            f"tone: {MATCHES}",
            f"Report: {(tmp_path / 'report.md').resolve().as_uri()}",
        ]

    def test_a_run_given_no_output_writes_where_the_default_names(
        self,
        started: StartedRuns,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(DEFAULT_OUTPUT, lambda: tmp_path / "stamped")

        assert dispatch(COMMANDS, [COMMAND, "bitphase", "--checkout", str(tmp_path)]) == 0
        assert [run.output for run in started.runs] == [tmp_path / "stamped"]

    def test_a_run_given_no_project_checks_the_corpus(self, started: StartedRuns, tmp_path: Path) -> None:
        assert dispatch(COMMANDS, [COMMAND, "bitphase", "--checkout", str(tmp_path)]) == 0
        assert started.projects == [[CORPUS_PROJECT]]

    def test_a_run_given_projects_checks_those_alone_in_the_order_given(
        self,
        started: StartedRuns,
        tmp_path: Path,
    ) -> None:
        for name in ("verse", "chorus"):
            ProjectContainer.save(Project.create(), tmp_path / f"{name}.stp")

        arguments = [
            COMMAND,
            "bitphase",
            "--checkout",
            str(tmp_path),
            "--project",
            str(tmp_path / "chorus.stp"),
            "--project",
            str(tmp_path / "verse.stp"),
        ]

        assert dispatch(COMMANDS, arguments) == 0
        assert started.projects == [["chorus", "verse"]]

    def test_a_project_that_fails_to_open_is_reported(self, started: StartedRuns, tmp_path: Path) -> None:
        arguments = [COMMAND, "bitphase", "--checkout", str(tmp_path), "--project", str(tmp_path / "absent.stp")]

        with pytest.raises(SystemExit, match="absent.stp"):
            dispatch(COMMANDS, arguments)

        assert not started.runs

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

    def test_the_famitracker_target_plays_through_the_program_given(
        self,
        started: StartedRuns,
        monkeypatch: pytest.MonkeyPatch,
        replaying_target: ReplayingTarget,
        tmp_path: Path,
    ) -> None:
        located: List[Path] = []

        def locate(cls: type, executable: Path) -> ReplayingTarget:
            located.append(executable)
            return replaying_target

        monkeypatch.setattr(FamiTrackerTarget, "located", classmethod(locate))
        executable = tmp_path / "FamiTracker.exe"

        assert dispatch(COMMANDS, [COMMAND, "famitracker", "--executable", str(executable)]) == 0
        assert located == [executable]
        assert [run.target for run in started.runs] == [replaying_target]

    def test_a_famitracker_that_cannot_run_is_reported(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        def located(cls: type, executable: Path) -> FamiTrackerTarget:
            raise FamiTrackerError("wine is missing")

        monkeypatch.setattr(FamiTrackerTarget, "located", classmethod(located))

        with pytest.raises(SystemExit, match="wine is missing"):
            dispatch(COMMANDS, [COMMAND, "famitracker", "--executable", str(tmp_path / "FamiTracker.exe")])

    def test_the_famitracker_program_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, [COMMAND, "famitracker"])

        assert leaving.value.code == 2

    def test_a_target_is_required(self) -> None:
        with pytest.raises(SystemExit) as leaving:
            dispatch(COMMANDS, [COMMAND])

        assert leaving.value.code == 2
