from argparse import ArgumentParser
from typing import Final, Sequence

from sampletones_shared.application import SAMPLETONES_NAME_VERSION
from sampletones_shared.command import Command

PROGRAM: Final[str] = "sampletones"
DESCRIPTION: Final[str] = "SampleToNES turns recordings into NES instruments and plays them back."
DEFAULT_COMMAND: Final[str] = "run"
COMMAND_FIELD: Final[str] = "command"
COMMAND_METAVAR: Final[str] = "<command>"


def build_parser(commands: Sequence[Command]) -> ArgumentParser:
    """The parser over ``commands``: one subcommand each, with the version and the help as flags.

    Args:
        commands: The commands on offer, listed in the help in this order.

    Returns:
        ArgumentParser: The parser the entry runs.

    Raises:
        ValueError: If two commands share a name.
    """
    names = [command.name for command in commands]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise ValueError(f"the commands share a name: {', '.join(repeated)}")

    parser = ArgumentParser(
        prog=PROGRAM,
        description=DESCRIPTION,
        epilog=f"Run '{PROGRAM} {COMMAND_METAVAR} --help' for a command's options.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=SAMPLETONES_NAME_VERSION,
    )
    subparsers = parser.add_subparsers(
        dest=COMMAND_FIELD,
        metavar=COMMAND_METAVAR,
        required=True,
    )

    for command in commands:
        subparser = subparsers.add_parser(command.name, help=command.help, description=command.help)
        command.configure(subparser)

    return parser


def dispatch(commands: Sequence[Command], argv: Sequence[str]) -> int:
    """Runs the command ``argv`` names, and the default command when it names none.

    Args:
        commands: The commands on offer.
        argv: The arguments after the program name.

    Returns:
        int: The exit status the command answers with.
    """
    parser = build_parser(commands)
    arguments = parser.parse_args(list(argv) or [DEFAULT_COMMAND])
    command = next(command for command in commands if command.name == arguments.command)
    return command.run(arguments)
