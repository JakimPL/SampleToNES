from argparse import ArgumentParser, Namespace
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

NAME: Final[str] = "btp"
HELP: Final[str] = "write example Bitphase documents (.btp) from the synthetic corpus"
SAMPLES_HELP: Final[str] = "write the corpus arrangement as Bitphase documents (.btp), at its own tempo and as a groove"


def configure(parser: ArgumentParser) -> None:
    actions = parser.add_subparsers(
        dest=ACTION_FIELD,
        metavar=ACTION_METAVAR,
        required=True,
    )
    add_output_option(
        actions.add_parser(SAMPLES, help=SAMPLES_HELP, description=SAMPLES_HELP),
    )


def run(arguments: Namespace) -> int:
    """Builds the corpus, writes its arrangement and prints each file written."""
    given = SamplesArguments(output=arguments.output)

    from sampletones_tools.samples.bitphase import write_samples
    from sampletones_tools.samples.emit import emit_samples

    return print_written(emit_samples(given.output, write_samples))


BTP: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
