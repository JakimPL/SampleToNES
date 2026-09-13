from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "icons"
HELP: Final[str] = "write the application icon suite from the mark"
DIRECTORY_HELP: Final[str] = "the directory receiving the icon files; without it, the icons the package ships"


@dataclass(frozen=True)
class IconsArguments:
    """What an icon suite run is given: where the files go, if anywhere but the package."""

    directory: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--directory", type=Path, default=None, help=DIRECTORY_HELP)


def run(arguments: Namespace) -> int:
    """Writes the icon suite and reports each file produced.

    Writing the icons the package ships needs a checkout, since that is where the package is.

    Raises:
        SystemExit: If the run writes the shipped icons outside a checkout.
    """
    given = IconsArguments(directory=arguments.directory)

    from sampletones_tools.checkout import require_checkout

    if given.directory is None:
        require_checkout(NAME)

    from sampletones_tools.assets.mark.specification import Mark
    from sampletones_tools.assets.mark.suite import write_icon_suite
    from sampletones_tools.assets.paths import ICONS_DIRECTORY

    for path in write_icon_suite(given.directory if given.directory is not None else ICONS_DIRECTORY, Mark.load()):
        print(f"Wrote {path}")

    return 0


ICONS: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
