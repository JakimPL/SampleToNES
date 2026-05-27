from pathlib import Path
from typing import Optional

from sampletones_application.application import Application
from sampletones_shared.constants.application import SAMPLETONES_NAME_VERSION
from sampletones_shared.logger import logger


def run_application(
    config_path: Optional[Path] = None,
    library_path: Optional[Path] = None,
    reconstruction_path: Optional[Path] = None,
) -> None:
    logger.info(SAMPLETONES_NAME_VERSION)
    gui = Application(config_path=config_path)
    gui.run()
