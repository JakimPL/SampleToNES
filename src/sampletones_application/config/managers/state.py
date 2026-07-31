from pathlib import Path
from typing import Optional

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml, save_yaml_atomic
from sampletones_shared.utils.system.paths import get_directory, to_path
from sampletones_shared.utils.validation import flatten_location, validate_with_recovery


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

        recovered = validate_with_recovery(ApplicationState, raw)
        if recovered.dropped:
            properties = ", ".join(flatten_location(location) for location in recovered.dropped)
            logger.warning(
                f"Application state file '{APPLICATION_STATE_PATH}' had incompatible settings"
                f" that were reset to defaults: {properties}"
            )

        return recovered.model

    def save(self) -> None:
        try:
            APPLICATION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            save_yaml_atomic(
                APPLICATION_STATE_PATH,
                self.state.model_dump(mode="json"),
            )
        except OSError as exception:
            logger.error_with_traceback(
                exception,
                f"File error while saving application state to {APPLICATION_STATE_PATH}",
            )

    def set_window_state(
        self,
        fullscreen: bool,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        self.state.viewport.fullscreen = fullscreen
        if not fullscreen:
            self.state.viewport.x = x
            self.state.viewport.y = y
            self.state.viewport.width = width
            self.state.viewport.height = height

    @property
    def fullscreen(self) -> bool:
        return self.state.viewport.fullscreen

    @property
    def window_x(self) -> int:
        return self.state.viewport.x

    @property
    def window_y(self) -> int:
        return self.state.viewport.y

    @property
    def window_width(self) -> int:
        return self.state.viewport.width

    @property
    def window_height(self) -> int:
        return self.state.viewport.height

    def set_current_tab(self, tab: Tab) -> None:
        self.state.current.tab = tab

    def toggle_show_advanced_settings(self) -> bool:
        self.state.advanced_settings = not self.state.advanced_settings
        return self.state.advanced_settings

    def is_card_collapsed(self, card_tag: str) -> bool:
        return self.state.collapsed_cards.get(card_tag, False)

    def set_card_collapsed(self, card_tag: str, collapsed: bool) -> None:
        self.state.collapsed_cards[card_tag] = collapsed

    def load_current_tab(self) -> Tab:
        return self.state.current.tab

    def set_current_reconstruction(self, path: Optional[Path]) -> None:
        self.state.current.reconstruction = path

    def set_current_project(self, path: Optional[Path]) -> None:
        self.state.current.project = path

    def set_config_path(self, path: Path) -> None:
        self.state.last_paths.config = get_directory(path)

    def get_config_path(self) -> Path:
        return self.state.last_paths.config

    def set_library_path(self, path: Path) -> None:
        self.state.last_paths.library = get_directory(path)

    def get_library_path(self) -> Path:
        return self.state.last_paths.library

    def set_instrument_path(self, path: Path) -> None:
        self.state.last_paths.instrument = get_directory(path)

    def get_instrument_path(self) -> Path:
        return self.state.last_paths.instrument

    def set_reconstruction_path(self, path: Path) -> None:
        self.state.last_paths.reconstruction = get_directory(path)

    def get_reconstruction_path(self) -> Path:
        return self.state.last_paths.reconstruction

    def set_audio_input_path(self, path: Path) -> None:
        self.state.last_paths.audio_input = get_directory(path)

    def get_audio_input_path(self) -> Path:
        return self.state.last_paths.audio_input

    def set_audio_path(self, path: Path) -> None:
        self.state.last_paths.audio = get_directory(path)

    def get_audio_path(self) -> Path:
        return self.state.last_paths.audio

    def set_project_path(self, path: Path) -> None:
        self.state.last_paths.project = get_directory(path)

    def get_project_path(self) -> Path:
        return self.state.last_paths.project

    @property
    def current_tab(self) -> Tab:
        return self.state.current.tab

    @property
    def current_reconstruction(self) -> Optional[Path]:
        return self.state.current.reconstruction

    @property
    def current_project(self) -> Optional[Path]:
        return self.state.current.project

    @property
    def advanced_settings(self) -> bool:
        return self.state.advanced_settings
