from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "driver"
HELP: Final[str] = "assemble the NES player driver and the cartridge shell with cc65"
OUTPUT_HELP: Final[str] = "the directory receiving the assembled images; without it, the ones the package ships"


@dataclass(frozen=True)
class DriverArguments:
    """What a driver build is given: where the image goes, if anywhere but the package."""

    output: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)


def run(arguments: Namespace) -> int:
    """Assembles the driver, then the shell around it, and prints the layout the build produced.

    Writing the images the package ships needs a checkout, since that is where the package is.

    Raises:
        SystemExit: If the build runs outside a checkout without an output of its own, or fails.
    """
    given = DriverArguments(output=arguments.output)

    from sampletones_tools.checkout import require_checkout

    if given.output is None:
        require_checkout(NAME)

    from sampletones_shared.exceptions.player import DriverBuildError
    from sampletones_tools.player.assembler.builder import build_driver
    from sampletones_tools.player.assembler.layout import BINARY_DIRECTORY, SHELL_DIRECTORY
    from sampletones_tools.player.assembler.report import layout_lines, shell_lines
    from sampletones_tools.player.assembler.shell import build_shell

    try:
        image = build_driver(given.output if given.output is not None else BINARY_DIRECTORY)
        shell = build_shell(given.output if given.output is not None else SHELL_DIRECTORY, image)
    except DriverBuildError as error:
        raise SystemExit(str(error)) from error

    for line in [*layout_lines(image), *shell_lines(shell)]:
        print(line)

    return 0


DRIVER: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
