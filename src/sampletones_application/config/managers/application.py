from pathlib import Path
from typing import Dict, Optional, Set

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_core.audio import AudioDeviceManager, CurrentDevice
from sampletones_core.constants.audio import BufferSize
from sampletones_core.paths import APPLICATION_CONFIG_PATH
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml, save_yaml_atomic
from sampletones_shared.utils.system.paths import to_path
from sampletones_shared.utils.validation import flatten_location, validate_with_recovery


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
        recovered = validate_with_recovery(ApplicationConfig, raw)
        if recovered.dropped:
            properties = ", ".join(flatten_location(location) for location in recovered.dropped)
            logger.warning(
                f"Application config file '{APPLICATION_CONFIG_PATH}' had incompatible settings"
                f" that were reset to defaults: {properties}"
            )

        return recovered.model

    def save(self) -> None:
        try:
            APPLICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            save_yaml_atomic(APPLICATION_CONFIG_PATH, self.config.model_dump())
        except OSError as exception:
            logger.error_with_traceback(
                exception,
                f"File error while saving application config to {APPLICATION_CONFIG_PATH}",
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
    def master_gain(self) -> float:
        return self.config.audio.master_gain

    def set_master_gain(self, value: float) -> None:
        self.config.audio.master_gain = value

    @property
    def palette_name(self) -> str:
        return self.config.display.palette

    def set_palette_name(self, name: str) -> None:
        self.config.display.palette = name

    @property
    def vsync(self) -> bool:
        return self.config.display.vsync

    def set_vsync(self, vsync: bool) -> None:
        self.config.display.vsync = vsync

    @property
    def max_fps(self) -> int:
        return self.config.display.max_fps

    def set_max_fps(self, max_fps: int) -> None:
        self.config.display.max_fps = max_fps

    @property
    def borderless(self) -> bool:
        return self.config.display.borderless

    def set_borderless(self, borderless: bool) -> None:
        self.config.display.borderless = borderless

    @property
    def shortcut_scheme_name(self) -> str:
        return self.config.shortcuts.scheme

    def set_shortcut_scheme_name(self, name: str) -> None:
        self.config.shortcuts.scheme = name

    @property
    def shortcut_overrides(self) -> Dict[str, Optional[str]]:
        return self.config.shortcuts.overrides

    def set_shortcut_overrides(
        self,
        overrides: Dict[str, Optional[str]],
    ) -> None:
        self.config.shortcuts.overrides = overrides

    @property
    def favorites(self) -> Set[Path]:
        return self.config.favorites.paths

    @property
    def autoplay(self) -> bool:
        return self.config.playback.autoplay

    def toggle_autoplay(self) -> bool:
        self.config.playback.autoplay = not self.config.playback.autoplay
        return self.config.playback.autoplay

    @property
    def follow_playback(self) -> bool:
        return self.config.playback.follow_playback

    def set_follow_playback(self, value: bool) -> None:
        self.config.playback.follow_playback = value

    @property
    def loop_song(self) -> bool:
        return self.config.playback.loop_song

    def set_loop_song(self, value: bool) -> None:
        self.config.playback.loop_song = value
