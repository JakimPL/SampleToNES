from pathlib import Path
from typing import Optional

from sampletones_application.config.application.state import ApplicationState
from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml, save_yaml_atomic
from sampletones_shared.utils.system.paths import to_path


class ApplicationStateManager:
    def __init__(self) -> None:
        self.state: ApplicationState = self._load()

    def _load(self) -> ApplicationState:
        if not APPLICATION_STATE_PATH.exists():
            return ApplicationState()

        raw = load_yaml(to_path(APPLICATION_STATE_PATH))
        if not raw or not isinstance(raw, dict):
            logger.warning(
                f"Application state file '{APPLICATION_STATE_PATH}' is empty or invalid." " Loading default state."
            )
            return ApplicationState()

        return ApplicationState(**raw)

    def save(self) -> None:
        try:
            APPLICATION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            save_yaml_atomic(APPLICATION_STATE_PATH, self.state.model_dump())
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(
                exception, f"File error while saving application state to {APPLICATION_STATE_PATH}"
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save application state to {APPLICATION_STATE_PATH}")

    def set_current_tab(self, tab: str) -> None:
        self.state.current_tab = tab

    def toggle_show_advanced_settings(self) -> bool:
        self.state.advanced_settings = not self.state.advanced_settings
        return self.state.advanced_settings

    def toggle_autoplay(self) -> bool:
        self.state.autoplay = not self.state.autoplay
        return self.state.autoplay

    def load_current_tab(self) -> str:
        return self.state.current_tab

    def set_current_reconstruction(self, path: Optional[Path]) -> None:
        self.state.current_reconstruction = path

    @property
    def current_tab(self) -> str:
        return self.state.current_tab

    @property
    def current_reconstruction(self) -> Optional[Path]:
        return self.state.current_reconstruction

    @property
    def advanced_settings(self) -> bool:
        return self.state.advanced_settings

    @property
    def autoplay(self) -> bool:
        return self.state.autoplay
