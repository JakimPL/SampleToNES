from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Tuple

from sampletones_shared.command import Command

NAME: Final[str] = "codec"
HELP: Final[str] = "measure the song codec on the synthetic corpus or on songs of this machine"
ACTION_FIELD: Final[str] = "action"
ACTION_METAVAR: Final[str] = "<action>"
REPORT: Final[str] = "report"
REPORT_HELP: Final[str] = "compress the synthetic corpus under every layer of the codec and write the report tables"
REPORT_OUTPUT_HELP: Final[str] = "the directory the report is written into, created when missing"
STUDY: Final[str] = "study"
STUDY_HELP: Final[str] = (
    "encode the projects and stems on this machine under every candidate change, with a verdict each"
)
MANIFEST_HELP: Final[str] = "a manifest a run wrote; its lengthening and variants stand in for the options below"
PROJECT_HELP: Final[str] = "a project file to measure in place of the corpus, repeatable"
RECONSTRUCTION_HELP: Final[str] = "a stem file, or a directory of stems, to measure in place of the corpus, repeatable"
OUTPUT_HELP: Final[str] = (
    "the directory the run writes into; without it, a timestamped directory under Documents/SampleToNES/compression"
)
LENGTHEN_HELP: Final[str] = "seconds each project's lengthened copy lasts"
VARIANTS_HELP: Final[str] = (
    "variants every song is encoded under, comma separated; without it every one, and the baseline always runs"
)
QUICK_HELP: Final[str] = "read one small project and one stem, to check the harness"
DEFAULT_LENGTHEN_SECONDS: Final[int] = 180


@dataclass(frozen=True)
class ReportArguments:
    """What a report run is given: the directory the tables are written into."""

    output: Path


@dataclass(frozen=True)
class StudyArguments:
    """What a study run is given, as written on the command line."""

    manifest: Optional[Path]
    projects: Tuple[Path, ...]
    reconstructions: Tuple[Path, ...]
    output: Optional[Path]
    lengthen: int
    variants: Optional[str]
    quick: bool


def configure(parser: ArgumentParser) -> None:
    actions = parser.add_subparsers(dest=ACTION_FIELD, metavar=ACTION_METAVAR, required=True)
    report = actions.add_parser(REPORT, help=REPORT_HELP, description=REPORT_HELP)
    report.add_argument("--output", "-o", type=Path, required=True, help=REPORT_OUTPUT_HELP)
    study = actions.add_parser(STUDY, help=STUDY_HELP, description=STUDY_HELP)
    study.add_argument("--manifest", type=Path, default=None, help=MANIFEST_HELP)
    study.add_argument("--project", type=Path, action="append", dest="projects", default=[], help=PROJECT_HELP)
    study.add_argument(
        "--reconstruction",
        type=Path,
        action="append",
        dest="reconstructions",
        default=[],
        help=RECONSTRUCTION_HELP,
    )
    study.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
    study.add_argument("--lengthen", type=int, default=DEFAULT_LENGTHEN_SECONDS, help=LENGTHEN_HELP)
    study.add_argument("--variants", type=str, default=None, help=VARIANTS_HELP)
    study.add_argument("--quick", action="store_true", help=QUICK_HELP)


def run(arguments: Namespace) -> int:
    """Measures the codec the way the action describes."""
    if arguments.action == REPORT:
        return _report(ReportArguments(output=arguments.output))

    return _study(
        StudyArguments(
            manifest=arguments.manifest,
            projects=tuple(arguments.projects),
            reconstructions=tuple(arguments.reconstructions),
            output=arguments.output,
            lengthen=arguments.lengthen,
            variants=arguments.variants,
            quick=arguments.quick,
        )
    )


def _report(given: ReportArguments) -> int:
    from sampletones_tools.codec.report.session import run_report

    for path in run_report(given.output):
        print(f"Wrote {path}")

    return 0


def _study(given: StudyArguments) -> int:
    from sampletones_tools.codec.study.session import resolve_manifest, run_study, variant_names

    manifest = resolve_manifest(
        given.manifest,
        projects=given.projects,
        reconstructions=given.reconstructions,
        lengthen_seconds=given.lengthen,
        variants=variant_names(given.variants),
        quick=given.quick,
    )
    run_study(manifest, given.output)
    return 0


CODEC: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
