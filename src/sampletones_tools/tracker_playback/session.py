from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple

from sampletones_tools.runs import stamped_run_directory
from sampletones_tools.tracker_playback.comparison import compare_traces
from sampletones_tools.tracker_playback.outcome import ProjectOutcome
from sampletones_tools.tracker_playback.paths import (
    DOCUMENTS_DIRECTORY_NAME,
    OUTPUT_ROOT,
    REPORT_FILENAME,
)
from sampletones_tools.tracker_playback.projects import CheckedProject
from sampletones_tools.tracker_playback.report import report_text
from sampletones_tools.tracker_playback.settings import PlaybackSettings
from sampletones_tools.tracker_playback.targets.protocol import PlaybackTarget
from sampletones_tools.tracker_playback.trace.application import application_trace


@dataclass(frozen=True)
class PlaybackRun:
    """What a check plays its projects through, where it writes, and how it reports.

    Attributes:
        target: The tracker the projects are exported to and played by.
        output: The directory the exported files, what their playing wrote and the report go into.
        settings: How the report shows what it finds.
    """

    target: PlaybackTarget
    output: Path
    settings: PlaybackSettings


@dataclass(frozen=True)
class PlaybackOutcome:
    """What a check found, and the report stating it.

    Attributes:
        outcomes: How each project fared, in the order they were played.
        report: The report written.
    """

    outcomes: Tuple[ProjectOutcome, ...]
    report: Path


def default_output() -> Path:
    """The directory a check given no output writes into: a timestamped one under Documents."""
    return stamped_run_directory(OUTPUT_ROOT)


def check_project(
    checked: CheckedProject,
    run: PlaybackRun,
) -> ProjectOutcome:
    """Plays one project through the target and holds what it played against the application.

    Args:
        checked: The project to check.
        run: What plays it, where the files go, and how differences are shown.

    Returns:
        ProjectOutcome: How the tracker played the project, and what the export reported leaving out.

    Raises:
        PlaybackError: If the tracker fails to play the project.
    """
    playback = run.target.play(
        checked.project,
        run.output / DOCUMENTS_DIRECTORY_NAME,
        checked.name,
    )
    return ProjectOutcome(
        project=checked,
        comparison=compare_traces(
            application_trace(checked.project),
            playback.trace,
            examples=run.settings.examples_per_difference,
        ),
        skipped_rows=playback.skipped_rows,
        truncation=playback.truncation,
    )


def check_projects(
    projects: Sequence[CheckedProject],
    run: PlaybackRun,
) -> PlaybackOutcome:
    """Checks each project and writes the report on all of them.

    The output keeps every exported file, and whatever its playing wrote, beside the report, so a
    difference can be followed into the file and the ticks that show it.

    Args:
        projects: The projects to check.
        run: What plays them, where the files go, and how differences are shown.

    Returns:
        PlaybackOutcome: How each project fared, and the report.

    Raises:
        PlaybackError: If the tracker fails to play a project.
    """
    (run.output / DOCUMENTS_DIRECTORY_NAME).mkdir(parents=True, exist_ok=True)
    outcomes = tuple(check_project(checked, run) for checked in projects)
    report = run.output / REPORT_FILENAME
    report.write_text(
        report_text(
            run.target,
            outcomes,
        ),
        encoding="utf-8",
    )
    return PlaybackOutcome(
        outcomes=outcomes,
        report=report,
    )
