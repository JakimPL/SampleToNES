from pathlib import Path
from typing import Set

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_core.audio import AudioDeviceManager, CurrentDevice
from sampletones_core.constants.audio import BufferSize
from sampletones_core.paths import APPLICATION_CONFIG_PATH
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml, save_yaml_atomic
from sampletones_shared.utils.system.paths import to_path


class ApplicationConfigManager:
    def __init__(self) -> None:
        self.config: ApplicationConfig = self._load()

    def _load(self) -> ApplicationConfig:
        if not APPLICATION_CONFIG_PATH.exists():
            logger.warning(
                f"Application config file '{APPLICATION_CONFIG_PATH}' does not exist." " Loading default configuration."
            )
            return ApplicationConfig()

        raw = load_yaml(to_path(APPLICATION_CONFIG_PATH))
        if not raw or not isinstance(raw, dict):
            logger.warning(
                f"Application config file '{APPLICATION_CONFIG_PATH}' is empty or invalid."
                " Loading default configuration."
            )
            return ApplicationConfig()

        raw.pop("state", None)
        return ApplicationConfig(**raw)

    def save(self) -> None:
        try:
            APPLICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            save_yaml_atomic(APPLICATION_CONFIG_PATH, self.config.model_dump())
        except (
            IOError,
            IsADirectoryError,
            PermissionError,
            OSError,
        ) as exception:
            logger.error_with_traceback(
                exception,
                f"File error while saving application config to {APPLICATION_CONFIG_PATH}",
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(
                exception,
                f"Failed to save application config to {APPLICATION_CONFIG_PATH}",
            )

    def toggle_favorite(self, path: Path) -> None:
        self.config.favorites.toggle_favorite(path)

    def set_current_audio_device(self, audio_device_manager: AudioDeviceManager) -> None:
        self.config.audio.set_audio_settings(audio_device_manager)

    @property
    def current_audio_device(self) -> CurrentDevice:
        return self.config.audio.current_device

    @property
    def current_buffer_size(self) -> BufferSize:
        return self.config.audio.buffer_size

    @property
    def favorites(self) -> Set[Path]:
        return self.config.favorites.paths
