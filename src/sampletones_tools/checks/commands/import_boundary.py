from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Tuple

from sampletones_shared.command import Command

NAME: Final[str] = "import-boundary"
HELP: Final[str] = "hold the source and scripts trees to the declared import boundaries"
FILES_HELP: Final[str] = "modules to check"
ALL_HELP: Final[str] = "check every module under the source and scripts trees instead of named files"
SOURCE_HELP: Final[str] = "source root the rule roots are named within; without it, the repository's src"
SCRIPTS_HELP: Final[str] = "scripts tree the standalone rules are written against; without it, the repository's scripts"


@dataclass(frozen=True)
class ImportBoundaryArguments:
    """What a boundary check is given: the modules or the whole trees, and where the trees are."""

    files: Tuple[Path, ...]
    everything: bool
    source: Optional[Path]
    scripts: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("files", nargs="*", type=Path, help=FILES_HELP)
    parser.add_argument("--all", action="store_true", help=ALL_HELP)
    parser.add_argument("--source", type=Path, default=None, help=SOURCE_HELP)
    parser.add_argument("--scripts", type=Path, default=None, help=SCRIPTS_HELP)


def run(arguments: Namespace) -> int:
    """Reports every import and token the boundaries forbid."""
    given = ImportBoundaryArguments(
        files=tuple(arguments.files),
        everything=arguments.all,
        source=arguments.source,
        scripts=arguments.scripts,
    )

    from sampletones_shared.paths.source import SCRIPTS_ROOT, SOURCE_ROOT
    from sampletones_tools.checks.import_boundary import check_imports, report

    selection = None if given.everything else {path.resolve() for path in given.files}
    violations = check_imports(
        given.source if given.source is not None else SOURCE_ROOT,
        given.scripts if given.scripts is not None else SCRIPTS_ROOT,
        selection,
    )
    return report(violations)


IMPORT_BOUNDARY: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
