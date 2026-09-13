from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones.commands.options import add_config_option
from sampletones_shared.command import Command

NAME: Final[str] = "library"
HELP: Final[str] = "generate the instruction library for a configuration"


@dataclass(frozen=True)
class LibraryArguments:
    """What a library generation is given: the configuration the library is built for, if any."""

    config: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    add_config_option(parser)


def run(arguments: Namespace) -> int:
    """Generates the instruction library for the configuration."""
    given = LibraryArguments(config=arguments.config)

    from sampletones_core.headless.config import load_config
    from sampletones_core.headless.library import generate_library
    from sampletones_shared.array import report_array_backend

    report_array_backend()
    generate_library(load_config(given.config))
    return 0


LIBRARY: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
