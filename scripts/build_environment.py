import argparse
import platform as running
import sys
from typing import Sequence

from bootstrap.platforms.factory import current_platform


def main(argv: Sequence[str]) -> int:
    """Prints the variables a build exports so audio playback compiles, one ``KEY=VALUE`` per line."""
    parser = argparse.ArgumentParser(description="Print the build environment audio playback compiles under.")
    parser.parse_args(list(argv))

    for line in current_platform().build_flags(machine=running.machine()):
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
