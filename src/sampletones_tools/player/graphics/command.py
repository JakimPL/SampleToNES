from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "tiles"
HELP: Final[str] = "draw the NES player's tile sheet into its pattern tables, and its screen into the shell's data"
OUTPUT_HELP: Final[str] = "the directory receiving the pattern tables; without it, the ones the package ships"
PREVIEW_HELP: Final[str] = "a directory receiving pictures of the screen and of the tile sheet"


@dataclass(frozen=True)
class TilesArguments:
    """What a tile build is given: where the tables go, and where its pictures go, if anywhere."""

    output: Optional[Path]
    preview: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
    parser.add_argument("--preview", "-p", type=Path, default=None, help=PREVIEW_HELP)


def run(arguments: Namespace) -> int:
    """Builds the pattern tables, and renders the screen where pictures are asked for.

    Writing the tables the package ships needs a checkout, since that is where the package is.

    Raises:
        SystemExit: If the build runs outside a checkout without an output of its own.
    """
    given = TilesArguments(output=arguments.output, preview=arguments.preview)

    from sampletones_tools.checkout import require_checkout

    if given.output is None:
        require_checkout(NAME)

    from sampletones_player.specification.shell import PATTERNS_NAME
    from sampletones_tools.player.assembler.layout import ASSEMBLY_DIRECTORY, INCLUDE_DIRECTORY, SOURCE_DIRECTORY
    from sampletones_tools.player.graphics.builder import build_patterns, build_shell_data
    from sampletones_tools.player.graphics.paths import PATTERNS_DIRECTORY
    from sampletones_tools.player.graphics.preview import write_previews

    destination = given.output if given.output is not None else PATTERNS_DIRECTORY
    patterns = build_patterns(destination)
    print(f"{PATTERNS_NAME}  {len(patterns)} bytes, {destination}")

    if given.output is None:
        build_shell_data(ASSEMBLY_DIRECTORY / INCLUDE_DIRECTORY, ASSEMBLY_DIRECTORY / SOURCE_DIRECTORY)
    else:
        build_shell_data(given.output, given.output)

    if given.preview is not None:
        for filepath in write_previews(given.preview):
            print(filepath)

    return 0


TILES: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
