from argparse import ArgumentParser
from pathlib import Path
from typing import Final

CONFIG_HELP: Final[str] = "a configuration .json file; without it, the saved configuration or the built-in defaults"


def add_config_option(parser: ArgumentParser) -> None:
    """Adds the ``--config`` option the commands reading a configuration share."""
    parser.add_argument("--config", "-c", type=Path, default=None, help=CONFIG_HELP)
