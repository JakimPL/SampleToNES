from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

ACTION_FIELD: Final[str] = "action"
ACTION_METAVAR: Final[str] = "<action>"
SAMPLES: Final[str] = "samples"
OUTPUT_HELP: Final[str] = "the directory the files are written into, created when missing"


@dataclass(frozen=True)
class SamplesArguments:
    """What an emitter run is given: the directory its files are written into."""

    output: Path


def add_output_option(parser: ArgumentParser) -> None:
    """Adds the required output directory an emitter writes into."""
    parser.add_argument("--output", "-o", type=Path, required=True, help=OUTPUT_HELP)


def print_written(paths: Sequence[Path]) -> int:
    """Prints each file an emitter wrote and returns the command's success status."""
    for path in paths:
        print(f"Wrote {path}")

    return 0
