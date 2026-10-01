from pathlib import Path
from typing import Final

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.settings import ProjectSettings
from sampletones_tools.tracker_playback.paths import (
    DOCUMENTS_DIRECTORY_NAME,
    OUTPUT_ROOT,
    REPORT_FILENAME,
)
from sampletones_tools.tracker_playback.projects import CheckedProject
from sampletones_tools.tracker_playback.session import PlaybackRun, check_projects, default_output
from sampletones_tools.tracker_playback.settings import PlaybackSettings
from tests.suite.performance import make_pulse_reconstruction, place_instrument, project_with_sample
from tests.suite.playback import ReplayingTarget

NAME: Final[str] = "tone"
SETTINGS: Final[PlaybackSettings] = PlaybackSettings(examples_per_difference=2)


def _checked_project() -> CheckedProject:
    project, sample = project_with_sample(
        make_pulse_reconstruction(count=4),
        rows_per_pattern=2,
        settings=ProjectSettings(tempo=150, speed=6, nes_frequency=60),
    )
    place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=sample, volume=15)
    return CheckedProject(name=NAME, purpose="A tone.", project=project)


class TestCheckProjects:
    def test_each_project_is_played_into_the_documents_and_the_report_is_written_beside_them(
        self,
        tmp_path: Path,
        replaying_target: ReplayingTarget,
    ) -> None:
        outcome = check_projects(
            (_checked_project(),),
            PlaybackRun(target=replaying_target, output=tmp_path, settings=SETTINGS),
        )

        assert replaying_target.played == [(tmp_path / DOCUMENTS_DIRECTORY_NAME, NAME)]
        assert outcome.report == tmp_path / REPORT_FILENAME
        assert replaying_target.title in outcome.report.read_text(encoding="utf-8")
        (project_outcome,) = outcome.outcomes
        assert project_outcome.project.name == NAME
        assert project_outcome.comparison.matches
        assert (project_outcome.skipped_rows, project_outcome.truncation) == (0, None)


class TestDefaultOutput:
    def test_a_run_given_no_output_lands_under_the_tools_documents_directory(self) -> None:
        assert default_output().parent == OUTPUT_ROOT
