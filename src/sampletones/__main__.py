import argparse
from argparse import RawTextHelpFormatter
from pathlib import Path

HELP_PATH = f"""Path to either:
    * audio file path/directory to reconstruct
    * reconstruction .json file to load a reconstruction
    * library .dat file to load a library"""

HELP_OUTPUT = """Output path for reconstruction."""

HELP_CONFIG = """Path to a configuration .json file
    (if not provided, default configuration will be used)"""

HELP_GENERATE = """Generate library data for given configuration
    (using default one if not provided)"""

HELP_HELP = """Show this help message and exit"""

HELP_VERSION = f"Show application version information"


def main() -> None:
    parser = argparse.ArgumentParser(prog="SampleToNES", add_help=False, formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help=HELP_PATH,
    )
    parser.add_argument("--output", "-o", type=str, default=None, help=HELP_OUTPUT)
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

    if args.help:
        parser.print_help()
        return

    if args.version:
        from sampletones.constants.application import SAMPLETONES_NAME_VERSION

        print(SAMPLETONES_NAME_VERSION)
        return

    if args.path and args.generate:
        raise RuntimeError("Only one action can be called at once.")

    config_path = Path(args.config) if args.config else None
    output_path = Path(args.output) if args.output else None

    from sampletones.configs import Config
    from sampletones.constants.paths import (
        EXT_FILE_JSON,
        EXT_FILE_LIBRARY,
        EXT_FILE_WAVE,
    )
    from sampletones.utils import logger

    config = Config.load(config_path) if config_path else Config()

    if args.generate:
        from sampletones.scripts import generate_library

        return generate_library(config, output_path)

    if args.path:
        path = Path(args.path)
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix == EXT_FILE_WAVE:
                from sampletones.scripts import reconstruct_file

                return reconstruct_file(path, config, output_path)
            elif suffix == EXT_FILE_JSON:
                from sampletones.scripts import load_reconstruction

                return load_reconstruction(path, config, output_path)
            elif suffix == EXT_FILE_LIBRARY:
                if output_path is not None:
                    logger.warning("Output path is ignored when loading a library.")
                from sampletones.scripts import load_library

                return load_library(path, config)
            else:
                raise RuntimeError(
                    f"Unsupported file extension, only {EXT_FILE_WAVE}, {EXT_FILE_JSON}, "
                    f"and {EXT_FILE_LIBRARY} are supported."
                )
        elif path.is_dir():
            from sampletones.scripts import reconstruct_directory

            return reconstruct_directory(path, config)
        else:
            raise RuntimeError("Unsupported path type or file extension.")

    from sampletones.scripts import run_application

    run_application(config_path)


if __name__ == "__main__":
    main()
