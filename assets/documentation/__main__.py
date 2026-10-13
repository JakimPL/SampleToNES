import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional, Sequence

from assets.documentation.build import SiteRequest, build_site
from assets.documentation.paths import DOCS_DIRECTORY, PROJECT_FILE, SITE_DIRECTORY

PROGRAM: Final[str] = "python -m assets.documentation"
DESCRIPTION: Final[str] = "write the user's documentation as HTML pages in the application's look"
OUTPUT_HELP: Final[str] = "the folder receiving the site; without it, the folder the package ships it from"


@dataclass(frozen=True)
class DocumentationArguments:
    """What a documentation run is given: where the site goes, if anywhere but the package."""

    output: Optional[Path]

    @classmethod
    def parse(cls, argv: Sequence[str]) -> "DocumentationArguments":
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
        """The folder the site is written into: the one given, or the one the package ships it from."""
        return self.output if self.output is not None else SITE_DIRECTORY


def main(argv: Sequence[str]) -> int:
    """Writes the documentation site and reports its index."""
    given = DocumentationArguments.parse(argv)
    site = build_site(SiteRequest(docs=DOCS_DIRECTORY, project=PROJECT_FILE, output=given.directory))
    print(f"Wrote {site.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
