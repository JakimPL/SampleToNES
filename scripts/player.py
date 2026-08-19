#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import Sequence

from sampletones_player.driver.assembler.builder import build_driver
from sampletones_player.driver.assembler.layout import BINARY_DIRECTORY
from sampletones_player.specification.driver import DRIVER_CODE_NAME
from sampletones_shared.exceptions import DriverBuildError


def main(argv: Sequence[str]) -> int:
    """Assembles the NES player driver and reports the layout the build produced."""

    parser = argparse.ArgumentParser(
        description="Assemble the NES player driver with cc65.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=BINARY_DIRECTORY,
        help="directory receiving the assembled driver",
    )
    arguments = parser.parse_args(list(argv))

    try:
        image = build_driver(arguments.directory)
    except DriverBuildError as error:
        print(error, file=sys.stderr)
        return 1

    addresses = image.addresses
    print(f"{DRIVER_CODE_NAME}  {len(image.code)} bytes, ${addresses.load:04X}-${addresses.song - 1:04X}")
    print(f"init        ${addresses.init:04X}")
    print(f"play        ${addresses.play:04X}")
    print(f"song        ${addresses.song:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
