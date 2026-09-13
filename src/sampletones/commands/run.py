from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command
from sampletones_shared.options import add_config_option

NAME: Final[str] = "run"
HELP: Final[str] = "start the application"


@dataclass(frozen=True)
class RunArguments:
    """What a run of the application is given: the configuration it starts with, if any."""

    config: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    add_config_option(parser)


def run(arguments: Namespace) -> int:
    """Starts the application."""
    given = RunArguments(config=arguments.config)

    from sampletones.run import run_application
    from sampletones_shared.array import report_array_backend

    report_array_backend()
    run_application(given.config)
    return 0


RUN: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
