import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Sequence

from assets.icons.mark.specification import Mark
from assets.icons.mark.suite import write_icon_suite
from assets.icons.paths import ICONS_DIRECTORY

PROGRAM: Final[str] = "python -m assets.icons"
DESCRIPTION: Final[str] = "write the application icon suite from the mark"
OUTPUT_HELP: Final[str] = "the directory receiving the icon files; without it, the icons the package ships"


@dataclass(frozen=True)
class IconsArguments:
    """What an icon suite run is given: where the files go, if anywhere but the package."""

    output: Optional[Path]

    @classmethod
    def parse(cls, argv: Sequence[str]) -> "IconsArguments":
        """The arguments ``argv`` states, read by the maker's own parser."""
        arguments = cls._parser().parse_args(list(argv))
        return cls(output=arguments.output)

    @staticmethod
    def _parser() -> ArgumentParser:
        parser = ArgumentParser(prog=PROGRAM, description=DESCRIPTION)
        parser.add_argument("--output", "-o", type=Path, default=None, help=OUTPUT_HELP)
        return parser

    @property
    def directory(self) -> Path:
        """The directory the suite is written into: the one given, or the one the icons ship from."""
        return self.output if self.output is not None else ICONS_DIRECTORY


def main(argv: Sequence[str]) -> int:
    """Writes the icon suite and reports each file produced."""
    given = IconsArguments.parse(argv)
    for path in write_icon_suite(given.directory, Mark.load()):
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
