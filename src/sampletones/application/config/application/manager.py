from sampletones.constants.paths import APPLICATION_CONFIG_PATH
from sampletones.utils.logger import logger

from .config import ApplicationConfig


class ApplicationConfigManager:
    def __init__(self) -> None:
        self.config: ApplicationConfig = self.load_config()

    def load_config(self) -> ApplicationConfig:
        return ApplicationConfig.default()

    def save_config(self) -> None:
        try:
            APPLICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.config.save(APPLICATION_CONFIG_PATH)
        except (IOError, OSError, PermissionError, IsADirectoryError) as exception:
            logger.error_with_traceback(
                exception, f"File error while saving application config from {APPLICATION_CONFIG_PATH}"
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save application config to {APPLICATION_CONFIG_PATH}")
