#!/usr/bin/env python3

"""
Writes the application icon suite from the packaged mark definition.

The mark, its template and the code drawing them live in `sampletones_assets/mark`; this
script points them at the directory the icons are shipped from.

Usage:
    python scripts/assets/icons.py            # write the suite into src/sampletones_assets/icons
"""

import argparse
import sys
from pathlib import Path
from typing import Final, Sequence

from sampletones_assets.mark.specification import Mark
from sampletones_assets.mark.suite import write_icon_suite

REPOSITORY_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
ICONS_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "src" / "sampletones_assets" / "icons"


def main(argv: Sequence[str]) -> int:
    """Writes the icon suite and reports each file it produced."""

    parser = argparse.ArgumentParser(
        description="Write the application icon suite from the mark definition.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=ICONS_DIRECTORY,
        help="directory receiving the icon files",
    )
    arguments = parser.parse_args(list(argv))

    for path in write_icon_suite(arguments.directory, Mark.load()):
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
