from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "palette-colors"
HELP: Final[str] = "hold every color to a palette token until it is drawn with"
PACKAGE_HELP: Final[str] = "package whose color reads to check; without it, the application package"
CONFIG_HELP: Final[str] = (
    "shipped configuration package whose colors must name palette tokens; without it, the shipped one"
)
PALETTES_HELP: Final[str] = "directory holding the palettes, where color values belong; without it, the shipped one"


@dataclass(frozen=True)
class PaletteColorsArguments:
    """What a palette check is given: the package, the configuration and the palettes."""

    package: Optional[Path]
    config_directory: Optional[Path]
    palettes: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--package", type=Path, default=None, help=PACKAGE_HELP)
    parser.add_argument("--config-directory", type=Path, default=None, help=CONFIG_HELP)
    parser.add_argument("--palettes", type=Path, default=None, help=PALETTES_HELP)


def run(arguments: Namespace) -> int:
    """Reports every color the application stores resolved or the configuration writes out."""
    given = PaletteColorsArguments(
        package=arguments.package,
        config_directory=arguments.config_directory,
        palettes=arguments.palettes,
    )

    from sampletones_application.paths import PALETTES_DIRECTORY
    from sampletones_shared.paths.resources import CONFIG_DIRECTORY
    from sampletones_tools.checks.palette_colors import (
        APPLICATION_PACKAGE,
        check_colors,
        report,
    )

    findings = check_colors(
        given.package if given.package is not None else APPLICATION_PACKAGE,
        given.config_directory if given.config_directory is not None else CONFIG_DIRECTORY,
        given.palettes if given.palettes is not None else PALETTES_DIRECTORY,
    )
    return report(findings)


PALETTE_COLORS: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
