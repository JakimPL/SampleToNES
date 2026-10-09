from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Command:
    """One named operation the ``sampletones`` entry runs: its options and what it does.

    A command module declares one of these at import time and keeps its implementation behind
    ``run``, so listing the commands loads nothing a command needs to do its work.

    Attributes:
        name: The word that selects the command on the command line.
        help: One line saying what the command does, shown in the command list.
        configure: Adds the command's arguments to the parser it is given.
        run: Performs the command over the parsed arguments and answers with the exit status.
    """

    name: str
    help: str
    configure: Callable[[ArgumentParser], None]
    run: Callable[[Namespace], int]
