from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sampletones_shared.command import Command

NAME: Final[str] = "nsf"
HELP: Final[str] = "render exported .nsf files to waves"
ACTION_FIELD: Final[str] = "action"
ACTION_METAVAR: Final[str] = "<action>"
RENDER: Final[str] = "render"
RENDER_HELP: Final[str] = "render the .nsf files in a directory to waves through ffmpeg's libgme demuxer"
DIRECTORY_HELP: Final[str] = "the directory holding the exported .nsf files"
TAIL_HELP: Final[str] = "seconds kept past the end of each song"
DEFAULT_TAIL_SECONDS: Final[float] = 0.5


@dataclass(frozen=True)
class RenderArguments:
    """What a render is given: the directory of exported files and the tail each wave keeps."""

    directory: Path
    tail: float


def configure(parser: ArgumentParser) -> None:
    actions = parser.add_subparsers(dest=ACTION_FIELD, metavar=ACTION_METAVAR, required=True)
    render = actions.add_parser(RENDER, help=RENDER_HELP, description=RENDER_HELP)
    render.add_argument("--directory", type=Path, required=True, help=DIRECTORY_HELP)
    render.add_argument("--tail", type=float, default=DEFAULT_TAIL_SECONDS, help=TAIL_HELP)


def run(arguments: Namespace) -> int:
    """Renders the exported files and prints each wave written.

    Raises:
        SystemExit: If ffmpeg is unusable or rejects a file.
    """
    given = RenderArguments(directory=arguments.directory, tail=arguments.tail)

    from sampletones_tools.samples.render import RenderingError, render_directory

    try:
        rendered = render_directory(given.directory, given.tail)
    except RenderingError as error:
        raise SystemExit(str(error)) from error

    for wave in rendered:
        print(f"{wave.destination}  {wave.seconds:.3f} s")

    return 0


NSF: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
