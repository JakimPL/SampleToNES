from argparse import ArgumentParser, Namespace
from typing import Final

from sampletones_shared.command import Command
from sampletones_tools.checks.registry import GATES

NAME: Final[str] = "check"
HELP: Final[str] = "hold the repository to one of its source checks"
GATE_FIELD: Final[str] = "gate"
GATE_METAVAR: Final[str] = "<check>"


def configure(parser: ArgumentParser) -> None:
    gates = parser.add_subparsers(dest=GATE_FIELD, metavar=GATE_METAVAR, required=True)
    for gate in GATES:
        gate.configure(gates.add_parser(gate.name, help=gate.help, description=gate.help))


def run(arguments: Namespace) -> int:
    """Runs the check named, from a checkout, and answers with its status.

    Raises:
        SystemExit: If the package runs outside a checkout.
    """
    gate = next(gate for gate in GATES if gate.name == arguments.gate)

    from sampletones_tools.checkout import require_checkout

    require_checkout(f"{NAME} {gate.name}")
    return gate.run(arguments)


CHECK: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
