from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Tuple

from sampletones_shared.command import Command
from sampletones_shared.options import add_config_option

NAME: Final[str] = "convert"
HELP: Final[str] = "reconstruct recordings into a .stn file"
SOURCES_HELP: Final[str] = "recordings mixed into one reconstruction, or one directory converted file by file"
OUTPUT_HELP: Final[str] = (
    "where the reconstruction is written; without it, the configuration's reconstructions directory"
)
CHANNELS_HELP: Final[str] = (
    "channels the reconstruction may use, comma separated: pulse1, pulse2, triangle, noise; "
    "without it pulse1, triangle and noise"
)
STEMS_HELP: Final[str] = "a JSON file holding a stems setup; its entries pair with the sources in order"


@dataclass(frozen=True)
class ConvertArguments:
    """What a conversion is given: the sources, where the result goes, and how the channels are handed out."""

    sources: Tuple[Path, ...]
    output: Optional[Path]
    config: Optional[Path]
    channels: Optional[str]
    stems: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("sources", nargs="+", type=Path, help=SOURCES_HELP)
    parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
    add_config_option(parser)
    setup = parser.add_mutually_exclusive_group()
    setup.add_argument("--channels", type=str, default=None, help=CHANNELS_HELP)
    setup.add_argument("--stems", type=Path, default=None, help=STEMS_HELP)


def run(arguments: Namespace) -> int:
    """Reconstructs the sources under the stems setup the options describe.

    Raises:
        SystemExit: If a source is missing or no recording, a channel is unknown, the stems file
            is missing or no setup, or the sources and the setup pair up wrong.
    """
    given = ConvertArguments(
        sources=tuple(arguments.sources),
        output=arguments.output,
        config=arguments.config,
        channels=arguments.channels,
        stems=arguments.stems,
    )

    from sampletones_core.headless.config import load_config
    from sampletones_core.headless.conversion.pairing import pairing_lines
    from sampletones_core.headless.conversion.request import (
        ConversionRequest,
        channels_named,
        classic_setup,
        load_stems,
    )
    from sampletones_core.headless.conversion.runners import reconstruct
    from sampletones_shared.array import report_array_backend
    from sampletones_shared.utils.validation import describe_failure

    try:
        stems = load_stems(given.stems) if given.stems is not None else classic_setup(channels_named(given.channels))
        request = ConversionRequest(sources=given.sources, stems=stems, output_path=given.output)
    except ValueError as error:
        raise SystemExit(describe_failure(error)) from error

    for line in pairing_lines(request):
        print(line)

    report_array_backend()
    reconstruct(request, load_config(given.config))
    return 0


CONVERT: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
