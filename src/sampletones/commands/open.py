from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from sampletones_shared.command import Command
from sampletones_shared.options import add_config_option

NAME: Final[str] = "open"
HELP: Final[str] = "start the application with a project, reconstruction or library loaded"
PATH_HELP: Final[str] = "a .stp project, a .stn reconstruction or an .ins library"


@dataclass(frozen=True)
class OpenArguments:
    """What an opening run is given: the file to load and the configuration to start with."""

    path: Path
    config: Optional[Path]


def configure(parser: ArgumentParser) -> None:
    parser.add_argument("path", type=Path, help=PATH_HELP)
    add_config_option(parser)


def run(arguments: Namespace) -> int:
    """Starts the application with the file loaded.

    Raises:
        SystemExit: If the path names no file, a recording, or a file of another kind.
    """
    given = OpenArguments(path=arguments.path, config=arguments.config)

    from sampletones_shared.paths.extensions import (
        EXT_FILE_LIBRARY,
        EXT_FILE_PROJECT,
        EXT_FILE_RECONSTRUCTION,
        EXT_FILES_AUDIO,
    )

    if not given.path.is_file():
        raise SystemExit(f"No file at {given.path}.")

    suffix = given.path.suffix.lower()
    if suffix in EXT_FILES_AUDIO:
        raise SystemExit(f"{given.path} is a recording; run: sampletones convert {given.path}")

    if suffix not in (EXT_FILE_PROJECT, EXT_FILE_RECONSTRUCTION, EXT_FILE_LIBRARY):
        raise SystemExit(
            f"{given.path} is neither a {EXT_FILE_PROJECT} project, a {EXT_FILE_RECONSTRUCTION} "
            f"reconstruction nor an {EXT_FILE_LIBRARY} library."
        )

    from sampletones.run import run_application
    from sampletones_shared.array import report_array_backend

    report_array_backend()
    run_application(
        given.config,
        project_path=given.path if suffix == EXT_FILE_PROJECT else None,
        reconstruction_path=given.path if suffix == EXT_FILE_RECONSTRUCTION else None,
        library_path=given.path if suffix == EXT_FILE_LIBRARY else None,
    )
    return 0


OPEN: Final[Command] = Command(
    name=NAME,
    help=HELP,
    configure=configure,
    run=run,
)
