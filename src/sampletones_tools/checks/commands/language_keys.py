from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command

NAME: Final[str] = "language-keys"
HELP: Final[str] = "hold the code and the language file to each other, in both directions"
SOURCE_HELP: Final[str] = "root of the sources to read; without it, the repository's src"
LANGUAGE_FILE_HELP: Final[str] = "language file to check against; without it, the shipped en.yaml"


@dataclass(frozen=True)
class LanguageKeysArguments:
    """What a language key check is given: the sources and the language file."""

    source: Optional[Path]
    language_file: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("--source", type=Path, default=None, help=SOURCE_HELP)
    parser.add_argument("--language-file", type=Path, default=None, help=LANGUAGE_FILE_HELP)


def run(arguments: Namespace) -> int:
    """Reports every disagreement between the language file and the lookups reading it."""
    given = LanguageKeysArguments(source=arguments.source, language_file=arguments.language_file)

    from sampletones_application.paths import LANG_EN
    from sampletones_shared.paths.source import SOURCE_ROOT
    from sampletones_tools.checks.language_keys import check_language_keys, report

    findings = check_language_keys(
        given.source if given.source is not None else SOURCE_ROOT,
        given.language_file if given.language_file is not None else LANG_EN,
    )
    return report(findings)


LANGUAGE_KEYS: Final[Command] = Command(name=NAME, help=HELP, configure=configure, run=run)
