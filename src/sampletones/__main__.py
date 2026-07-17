import argparse
import multiprocessing
from argparse import RawTextHelpFormatter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from sampletones_core.paths import EXT_FILES_AUDIO

if TYPE_CHECKING:
    from sampletones_core.configs import Config

HELP_PATH = """Path to either:
    * audio file path/directory to reconstruct
    * reconstruction .stn file to load a reconstruction
    * instructions library .ins file to load a library"""

HELP_OUTPUT = """Output path for reconstruction."""

HELP_CONFIG = """Path to a configuration .json file
    (if not provided, default configuration will be used)"""

HELP_GENERATE = """Generate library data for given configuration
    (using default one if not provided)"""

HELP_HELP = """Show this help message and exit"""

HELP_VERSION = "Show application version information"


@dataclass(frozen=True)
class ProgramArguments:
    path: Optional[Path] = None
    output: Optional[Path] = None
    config: Optional[Path] = None

    help: bool = False
    version: bool = False
    generate: bool = False


def _load_config(config_path: Optional[Path]) -> "Config":
    from sampletones_core.configs import Config

    return Config.load(config_path) if config_path else Config.default()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="SampleToNES",
        add_help=False,
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=HELP_PATH,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=HELP_OUTPUT,
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help=HELP_CONFIG,
    )
    parser.add_argument(
        "--generate",
        "-g",
        action="store_true",
        help=HELP_GENERATE,
    )
    parser.add_argument(
        "--help",
        "-h",
        action="store_true",
        help=HELP_HELP,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help=HELP_VERSION,
    )
    args: ProgramArguments = ProgramArguments(**vars(parser.parse_args()))

    if args.help:
        parser.print_help()
        return None

    if args.version:
        from sampletones_shared.application import (
            SAMPLETONES_NAME_VERSION,
        )

        return print(SAMPLETONES_NAME_VERSION)

    config_path = Path(args.config) if args.config else None
    output_path = Path(args.output) if args.output else None

    from sampletones_core.paths import (
        EXT_FILE_LIBRARY,
        EXT_FILE_PROJECT,
        EXT_FILE_RECONSTRUCTION,
    )

    if args.generate:
        from sampletones_core.scripts.library import generate_library

        config = _load_config(config_path)
        return generate_library(config)

    project_path: Optional[Path] = None
    library_path: Optional[Path] = None
    reconstruction_path: Optional[Path] = None

    if args.path:
        path = Path(args.path)
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix == EXT_FILE_PROJECT:
                project_path = path

            elif suffix == EXT_FILE_RECONSTRUCTION:
                reconstruction_path = path

            elif suffix == EXT_FILE_LIBRARY:
                library_path = path

            elif suffix in EXT_FILES_AUDIO:
                from sampletones_core.scripts.reconstruction import (
                    reconstruct_file,
                )

                config = _load_config(config_path)
                return reconstruct_file(path, config, output_path)

            else:
                raise RuntimeError(
                    f"Unsupported file extension, only audio ({', '.join(EXT_FILES_AUDIO)}),"
                    f"{EXT_FILE_RECONSTRUCTION} reconstruction, "
                    f"and {EXT_FILE_LIBRARY} library files are supported."
                )

        elif path.is_dir():
            from sampletones_core.scripts.reconstruction import (
                reconstruct_directory,
            )

            config = _load_config(config_path)
            return reconstruct_directory(path, config)

        else:
            raise RuntimeError("Unsupported path type or file extension.")

    from sampletones.run import run_application

    return run_application(
        config_path,
        library_path=library_path,
        reconstruction_path=reconstruction_path,
        project_path=project_path,
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
