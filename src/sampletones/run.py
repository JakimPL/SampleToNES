from pathlib import Path
from typing import Optional

from sampletones_application.prototype.coordinator import PrototypeWindowCoordinator
from sampletones_shared.constants.application import SAMPLETONES_NAME_VERSION
from sampletones_shared.logger import logger


def run_application(
    config_path: Optional[Path] = None,
    library_path: Optional[Path] = None,
    reconstruction_path: Optional[Path] = None,
) -> None:
    logger.info(SAMPLETONES_NAME_VERSION)
    coordinator = PrototypeWindowCoordinator()
    coordinator.run()
