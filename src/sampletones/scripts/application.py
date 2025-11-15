from pathlib import Path
from typing import Optional

from sampletones.application import GUI
from sampletones.constants.application import SAMPLETONES_NAME_VERSION
from sampletones.utils.logger import logger


def run_application(
    config_path: Optional[Path] = None,
    library_path: Optional[Path] = None,
    reconstruction_path: Optional[Path] = None,
) -> None:
    logger.info(SAMPLETONES_NAME_VERSION)
    application = GUI(config_path)
    try:
        application.run()
    except KeyboardInterrupt:
        logger.info("Application terminated")
    else:
        logger.info("Application closed")
