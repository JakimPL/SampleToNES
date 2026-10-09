from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sampletones_shared.command import Command
from sampletones_tools.samples.commands.options import (
    ACTION_FIELD,
    ACTION_METAVAR,
    SAMPLES,
    SamplesArguments,
    add_output_option,
    print_written,
)

NAME: Final[str] = "nsf"
HELP: Final[str] = "write example .nsf files from the synthetic corpus and render .nsf files to waves"
SAMPLES_HELP: Final[str] = "write each corpus sample and the corpus arrangement as .nsf files"
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
    actions = parser.add_subparsers(
        dest=ACTION_FIELD,
        metavar=ACTION_METAVAR,
        required=True,
    )
    samples = actions.add_parser(
        SAMPLES,
        help=SAMPLES_HELP,
        description=SAMPLES_HELP,
    )
    add_output_option(samples)
    render = actions.add_parser(
        RENDER,
        help=RENDER_HELP,
        description=RENDER_HELP,
    )
    render.add_argument(
        "--directory",
        type=Path,
        required=True,
        help=DIRECTORY_HELP,
    )
    render.add_argument(
        "--tail",
        type=float,
        default=DEFAULT_TAIL_SECONDS,
        help=TAIL_HELP,
    )


def run(arguments: Namespace) -> int:
    """Writes the example files or renders exported ones, as the action names."""
    if arguments.action == SAMPLES:
        return _write_samples(SamplesArguments(output=arguments.output))

    return _render(
        RenderArguments(directory=arguments.directory, tail=arguments.tail),
    )


def _write_samples(given: SamplesArguments) -> int:
    from sampletones_tools.samples.emit import emit_samples
    from sampletones_tools.samples.nsf import write_samples

    return print_written(emit_samples(given.output, write_samples))


def _render(given: RenderArguments) -> int:
    """Renders the exported files and prints each wave written.

    Raises:
        SystemExit: If ffmpeg is unusable or rejects a file.
    """
    from sampletones_tools.samples.render import RenderingError, render_directory

    try:
        rendered = render_directory(given.directory, given.tail)
    except RenderingError as error:
        raise SystemExit(str(error)) from error

    for wave in rendered:
        print(f"{wave.destination}  {wave.seconds:.3f} s")

    return 0


NSF: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
