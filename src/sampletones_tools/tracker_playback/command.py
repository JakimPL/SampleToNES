from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Optional, Tuple

from sampletones_shared.command import Command
from sampletones_tools.tracker_playback.commands.bitphase import BITPHASE
from sampletones_tools.tracker_playback.commands.face import TargetFace

NAME: Final[str] = "tracker-playback"
HELP: Final[str] = (
    "export a corpus of projects to a tracker, play each file with the tracker's own code, "
    "and report every tick a channel sounds differently from the app"
)
TARGET_FIELD: Final[str] = "target"
TARGET_METAVAR: Final[str] = "<target>"
OUTPUT_HELP: Final[str] = (
    "the directory the run writes into; without it, a timestamped directory under "
    "Documents/SampleToNES/tracker-playback"
)
TARGETS: Final[Tuple[TargetFace, ...]] = (BITPHASE,)
TARGETS_BY_NAME: Final[Dict[str, TargetFace]] = {face.name: face for face in TARGETS}


@dataclass(frozen=True)
class PlaybackArguments:
    """What a check is given beside its target's own options: the target, and where it writes, if anywhere."""

    target: str
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
            "--output",
            "-o",
            type=Path,
            default=None,
            help=OUTPUT_HELP,
        )


def run(arguments: Namespace) -> int:
    """Plays the corpus through the target the command names, prints each verdict and the report's link.

    Raises:
        SystemExit: If the target's tracker, or what runs it, is missing, or it fails to play a file.
    """
    given = PlaybackArguments(target=arguments.target, output=arguments.output)
    face = TARGETS_BY_NAME[given.target]

    from sampletones_tools.tracker_playback.corpus.build import comparison_corpus
    from sampletones_tools.tracker_playback.corpus.spec import CorpusSpec
    from sampletones_tools.tracker_playback.report import result_label
    from sampletones_tools.tracker_playback.session import (
        PlaybackRun,
        check_corpus,
        default_output,
    )
    from sampletones_tools.tracker_playback.settings import PlaybackSettings
    from sampletones_tools.tracker_playback.targets.protocol import PlaybackError

    try:
        target = face.locate(arguments)
        outcome = check_corpus(
            comparison_corpus(CorpusSpec.load()),
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


TRACKER_PLAYBACK: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
