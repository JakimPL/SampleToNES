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

NAME: Final[str] = "rom"
HELP: Final[str] = "write example .nes cartridges from the synthetic corpus"
SAMPLES_HELP: Final[str] = "write each corpus sample and the corpus arrangement as .nes cartridges"


def configure(parser: ArgumentParser) -> None:
    actions = parser.add_subparsers(dest=ACTION_FIELD, metavar=ACTION_METAVAR, required=True)
    samples = actions.add_parser(SAMPLES, help=SAMPLES_HELP, description=SAMPLES_HELP)
    add_output_option(samples)


def run(arguments: Namespace) -> int:
    """Writes the example cartridges."""
    given = SamplesArguments(output=arguments.output)

    from sampletones_tools.samples.emit import emit_samples
    from sampletones_tools.samples.rom import write_samples

    return print_written(emit_samples(given.output, write_samples))


ROM: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
