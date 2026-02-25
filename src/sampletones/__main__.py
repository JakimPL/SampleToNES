import argparse
import multiprocessing
from argparse import RawTextHelpFormatter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sampletones.constants.paths import EXT_FILES_AUDIO

HELP_PATH = """Path to either:
    * audio file path/directory to reconstruct
    * reconstruction .json file to load a reconstruction
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
        from sampletones.constants.application import SAMPLETONES_NAME_VERSION

        return print(SAMPLETONES_NAME_VERSION)

    if args.path and args.generate:
        raise RuntimeError("Only one action can be called at once.")

    config_path = Path(args.config) if args.config else None
    output_path = Path(args.output) if args.output else None

    from sampletones.configs import Config
    from sampletones.constants.paths import EXT_FILE_LIBRARY, EXT_FILE_RECONSTRUCTION
    from sampletones.utils.logger import logger

    config = Config.load(config_path) if config_path else Config.default()

    if args.generate:
        from sampletones.scripts import generate_library

        if output_path is not None:
            logger.warning("Output path is ignored when generating a library")

        return generate_library(config)

    if args.path:
        path = Path(args.path)
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix in EXT_FILES_AUDIO:
                from sampletones.scripts import reconstruct_file

                return reconstruct_file(path, config, output_path)

            if suffix == EXT_FILE_RECONSTRUCTION:
                from sampletones.scripts import load_reconstruction

                return load_reconstruction(path, config_path)

            if suffix == EXT_FILE_LIBRARY:
                if output_path is not None:
                    logger.warning("Output path is ignored when loading a library")
                from sampletones.scripts import load_library

                return load_library(path, config_path)

            raise RuntimeError(
                f"Unsupported file extension, only audio ({', '.join(EXT_FILES_AUDIO)}),"
                f"{EXT_FILE_RECONSTRUCTION} reconstruction, "
                f"and {EXT_FILE_LIBRARY} library files are supported."
            )

        if path.is_dir():
            from sampletones.scripts import reconstruct_directory

            return reconstruct_directory(path, config)

        raise RuntimeError("Unsupported path type or file extensio.")

    from sampletones.scripts import run_application

    return run_application(config_path)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
    multiprocessing.freeze_support()
    main()
