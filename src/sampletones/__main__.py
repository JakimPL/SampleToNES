import argparse
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import Optional

from sampletones.constants.application import SAMPLETONES_NAME, SAMPLETONES_NAME_VERSION
from sampletones.constants.paths import EXT_FILE_JSON, EXT_FILE_LIBRARY, EXT_FILE_WAVE
from sampletones.utils import logger

HELP_PATH = f"""Path to either:
    * audio file path/directory to reconstruct
    * reconstruction {EXT_FILE_JSON} file to load a reconstruction
    * library {EXT_FILE_LIBRARY} file to load a library"""

HELP_CONFIG = """Path to a configuration {EXT_FILE_JSON} file
(if not provided, default configuration will be used)"""

HELP_GENERATE = """Generate library data for given configuration
(using default one if not provided)"""

HELP_HELP = """Show this help message and exit"""

HELP_VERSION = f"Show {SAMPLETONES_NAME} version information"


def reconstruct_file(path: Path, config_path: Optional[Path] = None) -> None:
    pass


def reconstruct_directory(path: Path, config_path: Optional[Path] = None) -> None:
    pass


def load_reconstruction(path: Path, config_path: Optional[Path] = None) -> None:
    pass


def load_library(path: Path, config_path: Optional[Path] = None) -> None:
    pass


def generate_library(config_path: Optional[Path] = None) -> None:
    pass


def run_application(config_path: Optional[Path] = None) -> None:
    from sampletones.application.gui import GUI

    logger.info(SAMPLETONES_NAME_VERSION)
    application = GUI(config_path)
    try:
        application.run()
    except KeyboardInterrupt:
        logger.info("Application terminated")
    else:
        logger.info("Application closed")


def main() -> None:
    parser = argparse.ArgumentParser(prog=SAMPLETONES_NAME, add_help=False, formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=HELP_PATH,
    )
    parser.add_argument("--config", "-c", type=str, default=None, help=HELP_CONFIG)
    parser.add_argument(
        "--generate",
        "-g",
        action="store_true",
        help=HELP_GENERATE,
    )
    parser.add_argument("--help", "-h", action="store_true", help=HELP_HELP)
    parser.add_argument("--version", "-v", action="store_true", help=HELP_VERSION)

    args = parser.parse_args()
    config_path = Path(args.config) if args.config else None

    if args.help:
        parser.print_help()
        return

    if args.version:
        logger.info(SAMPLETONES_NAME_VERSION)
        return

    if args.path and args.generate:
        raise RuntimeError("Only one action can be called at once.")

    if args.generate:
        return generate_library(config_path)

    if args.path:
        path = Path(args.path)
        config_path = config_path
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix == EXT_FILE_WAVE:
                return reconstruct_file(path, config_path)
            elif suffix == EXT_FILE_JSON:
                return load_reconstruction(path, config_path)
            elif suffix == EXT_FILE_LIBRARY:
                return load_library(path, config_path)
            else:
                raise RuntimeError(
                    f"Unsupported file extension, only {EXT_FILE_WAVE}, {EXT_FILE_JSON}, "
                    f"and {EXT_FILE_LIBRARY} are supported."
                )
        elif path.is_dir():
            return reconstruct_directory(path, config_path)
        else:
            raise RuntimeError("Unsupported path type or file extension.")

    run_application(config_path)


if __name__ == "__main__":
    main()
