from argparse import ArgumentParser, Namespace
from typing import Final

from sampletones_shared.command import Command

NAME: Final[str] = "compatibility"
HELP: Final[str] = "archive one document per stored format at the version this build writes"
OUTPUT_FLAGS: Final[tuple[str, str]] = ("-o", "--output")
FORCE_FLAG: Final[str] = "--force"
OUTPUT_FIELD: Final[str] = "output"
FORCE_FIELD: Final[str] = "force"


def configure(parser: ArgumentParser) -> None:
    parser.add_argument(
        *OUTPUT_FLAGS,
        dest=OUTPUT_FIELD,
        default=None,
        help="the corpus the files are written into; the repository's own by default",
    )
    parser.add_argument(
        FORCE_FLAG,
        dest=FORCE_FIELD,
        action="store_true",
        help="write a version that is already archived again",
    )


def run(arguments: Namespace) -> int:
    """Archives the corpus and names what it wrote.

    Raises:
        SystemExit: If the package runs outside a checkout.
    """
    from pathlib import Path

    from sampletones_tools.checkout import require_checkout
    from sampletones_tools.compatibility.paths import CORPUS_DIRECTORY
    from sampletones_tools.compatibility.writer import archive

    require_checkout(NAME)
    output = arguments.output
    root = CORPUS_DIRECTORY if output is None else Path(output)
    written = archive(root, arguments.force)
    for path in written:
        print(f"wrote {path} ({path.stat().st_size} bytes)")

    if not written:
        print(f"every version this build writes is already archived in {root}")

    return 0


COMPATIBILITY: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
