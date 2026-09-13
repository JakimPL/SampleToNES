from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "icons"
HELP: Final[str] = "write the application icon suite from the mark"
OUTPUT_HELP: Final[str] = "the directory receiving the icon files; without it, the icons the package ships"


@dataclass(frozen=True)
class IconsArguments:
    """What an icon suite run is given: where the files go, if anywhere but the package."""

    output: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)


def run(arguments: Namespace) -> int:
    """Writes the icon suite and reports each file produced.

    The suite is rasterized with Pillow, which the project environment carries, so the command
    runs from a checkout wherever it writes.

    Raises:
        SystemExit: If the run happens outside a checkout.
    """
    given = IconsArguments(output=arguments.output)

    from sampletones_tools.checkout import require_checkout

    require_checkout(NAME)

    from sampletones_tools.assets.mark.specification import Mark
    from sampletones_tools.assets.mark.suite import write_icon_suite
    from sampletones_tools.assets.paths import ICONS_DIRECTORY

    for path in write_icon_suite(given.output if given.output is not None else ICONS_DIRECTORY, Mark.load()):
        print(f"Wrote {path}")

    return 0


ICONS: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
