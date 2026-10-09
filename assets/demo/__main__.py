import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

from assets.demo.tree import build_demo

PROGRAM: Final[str] = "python -m assets.demo"
DESCRIPTION: Final[str] = "make the demo tree: recordings, a library, reconstructions and a project"
OUTPUT_HELP: Final[str] = "the empty folder the tree is written into, created when missing"


@dataclass(frozen=True)
class DemoArguments:
    """What a demo run is given: the folder the tree is written into."""

    output: Path

    @classmethod
    def parse(cls, argv: Sequence[str]) -> "DemoArguments":
        """The arguments ``argv`` states, read by the maker's own parser."""
        parser = ArgumentParser(prog=PROGRAM, description=DESCRIPTION)
        parser.add_argument("--output", "-o", type=Path, required=True, help=OUTPUT_HELP)
        return cls(output=parser.parse_args(list(argv)).output)


def main(argv: Sequence[str]) -> int:
    """Writes the demo tree and reports each file produced."""
    given = DemoArguments.parse(argv)
    for path in build_demo(given.output):
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
