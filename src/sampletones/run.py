from pathlib import Path
from typing import Optional

from sampletones_application.application import Application
from sampletones_application.config.profile import UserProfile
from sampletones_shared.application import SAMPLETONES_NAME_VERSION
from sampletones_shared.logger import logger


def run_application(
    config_path: Optional[Path] = None,
    *,
    library_path: Optional[Path] = None,
    reconstruction_path: Optional[Path] = None,
    project_path: Optional[Path] = None,
) -> None:
    logger.info(SAMPLETONES_NAME_VERSION)
    gui = Application(
        profile=UserProfile.user(),
        config_path=config_path,
        library_path=library_path,
        reconstruction_path=reconstruction_path,
        project_path=project_path,
    )
    gui.run()
