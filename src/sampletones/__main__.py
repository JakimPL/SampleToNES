import multiprocessing
import sys

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch


def main() -> int:
    """Runs the command named on the command line, which is what the ``sampletones`` entry does."""
    return dispatch(COMMANDS, sys.argv[1:])


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
