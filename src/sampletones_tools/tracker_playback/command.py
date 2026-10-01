from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Final, List, Optional, Tuple

from sampletones_shared.command import Command
from sampletones_tools.tracker_playback.commands.bitphase import BITPHASE
from sampletones_tools.tracker_playback.commands.face import TargetFace

if TYPE_CHECKING:
    from sampletones_tools.tracker_playback.projects import CheckedProject

NAME: Final[str] = "tracker-playback"
HELP: Final[str] = (
    "export projects to a tracker, play each file with the tracker's own code, "
    "and report every tick a channel sounds differently from the app"
)
TARGET_FIELD: Final[str] = "target"
TARGET_METAVAR: Final[str] = "<target>"
PROJECT_HELP: Final[str] = (
    "a project file (.stp) to check; repeat it to check several. Without it, the run checks the corpus "
    "that comes with the package"
)
PROJECT_METAVAR: Final[str] = "<file.stp>"
OUTPUT_HELP: Final[str] = (
    "the directory the run writes into; without it, a timestamped directory under "
    "Documents/SampleToNES/tracker-playback"
)
TARGETS: Final[Tuple[TargetFace, ...]] = (BITPHASE,)
TARGETS_BY_NAME: Final[Dict[str, TargetFace]] = {face.name: face for face in TARGETS}


@dataclass(frozen=True)
class PlaybackArguments:
    """What a check is given beside its target's own options.

    Attributes:
        target: The target's name.
        projects: The project files to check, or none to check the corpus.
        output: Where the run writes, or ``None`` for a timestamped directory.
    """

    target: str
    projects: Tuple[Path, ...]
    output: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    targets = parser.add_subparsers(
        dest=TARGET_FIELD,
        metavar=TARGET_METAVAR,
        required=True,
    )
    for face in TARGETS:
        target = targets.add_parser(
            face.name,
            help=face.help,
            description=face.help,
        )
        face.configure(target)
        target.add_argument(
            "--project",
            dest="projects",
            type=Path,
            action="append",
            default=None,
            metavar=PROJECT_METAVAR,
            help=PROJECT_HELP,
        )
        target.add_argument(
            "--output",
            "-o",
            type=Path,
            default=None,
            help=OUTPUT_HELP,
        )


def run(arguments: Namespace) -> int:
    """Plays the projects given, or the corpus, through the target the command names, and prints each verdict.

    The report's link follows the verdicts.

    Raises:
        SystemExit: If a project file fails to open, the target's tracker or what runs it is missing, or
            the tracker fails to play a file.
    """
    given = PlaybackArguments(
        target=arguments.target,
        projects=tuple(arguments.projects) if arguments.projects is not None else (),
        output=arguments.output,
    )
    face = TARGETS_BY_NAME[given.target]

    from sampletones_tools.tracker_playback.report import result_label
    from sampletones_tools.tracker_playback.session import (
        PlaybackRun,
        check_projects,
        default_output,
    )
    from sampletones_tools.tracker_playback.settings import PlaybackSettings
    from sampletones_tools.tracker_playback.targets.protocol import PlaybackError

    try:
        target = face.locate(arguments)
        outcome = check_projects(
            checked_projects(given.projects),
            PlaybackRun(
                target=target,
                output=given.output if given.output is not None else default_output(),
                settings=PlaybackSettings.load(),
            ),
        )
    except PlaybackError as error:
        raise SystemExit(str(error)) from error

    for project in outcome.outcomes:
        print(f"{project.project.name}: {result_label(project.comparison)}")

    print(f"Report: {outcome.report.resolve().as_uri()}")
    return 0


def checked_projects(paths: Tuple[Path, ...]) -> List[CheckedProject]:
    """The projects saved in ``paths``, or the corpus that comes with the package where none is given.

    Raises:
        SystemExit: If a project file fails to open, naming why.
    """
    from sampletones_shared.exceptions.project import LoadProjectError
    from sampletones_tools.tracker_playback.corpus.build import comparison_corpus
    from sampletones_tools.tracker_playback.corpus.spec import CorpusSpec
    from sampletones_tools.tracker_playback.projects import loaded_projects

    if not paths:
        return comparison_corpus(CorpusSpec.load())

    try:
        return loaded_projects(paths)
    except (LoadProjectError, OSError) as error:
        raise SystemExit(str(error)) from error


TRACKER_PLAYBACK: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
