from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "driver"
HELP: Final[str] = "assemble the NES player driver with cc65"
DIRECTORY_HELP: Final[str] = "the directory receiving the assembled driver; without it, the driver the package ships"


@dataclass(frozen=True)
class DriverArguments:
    """What a driver build is given: where the image goes, if anywhere but the package."""

    directory: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--directory", type=Path, default=None, help=DIRECTORY_HELP)


def run(arguments: Namespace) -> int:
    """Assembles the driver and prints the layout the build produced.

    Writing the driver the package ships needs a checkout, since that is where the package is.

    Raises:
        SystemExit: If the build runs outside a checkout without a directory of its own, or fails.
    """
    given = DriverArguments(directory=arguments.directory)

    from sampletones_tools.checkout import require_checkout

    if given.directory is None:
        require_checkout(NAME)

    from sampletones_shared.exceptions.player import DriverBuildError
    from sampletones_tools.player.assembler.builder import build_driver
    from sampletones_tools.player.assembler.layout import BINARY_DIRECTORY
    from sampletones_tools.player.assembler.report import layout_lines

    try:
        image = build_driver(given.directory if given.directory is not None else BINARY_DIRECTORY)
    except DriverBuildError as error:
        raise SystemExit(str(error)) from error

    for line in layout_lines(image):
        print(line)

    return 0


DRIVER: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
