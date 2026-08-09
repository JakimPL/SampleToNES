from pathlib import Path
from typing import Dict, Optional, Set

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.application import ApplicationConfigManager
from sampletones_application.config.managers.state import ApplicationStateManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.state.state import ApplicationState
from sampletones_core.audio import AudioDeviceManager, CurrentDevice
from sampletones_core.constants.audio import BufferSize


class SessionManager:
    def __init__(self, profile: UserProfile) -> None:
        self._config_manager = ApplicationConfigManager(profile.config)
        self._state_manager = ApplicationStateManager(profile.state)

    @property
    def config(self) -> ApplicationConfig:
        return self._config_manager.config

    @property
    def state(self) -> ApplicationState:
        return self._state_manager.state

    def set_window_state(
        self,
        fullscreen: bool,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        self._state_manager.set_window_state(
            fullscreen,
            x,
            y,
            width,
            height,
        )

    def set_current_tab(self, tab: Tab) -> None:
        self._state_manager.set_current_tab(tab)

    def toggle_show_advanced_settings(self) -> bool:
        return self._state_manager.toggle_show_advanced_settings()

    def is_card_collapsed(self, card_tag: str) -> bool:
        return self._state_manager.is_card_collapsed(card_tag)

    def set_card_collapsed(self, card_tag: str, collapsed: bool) -> None:
        self._state_manager.set_card_collapsed(card_tag, collapsed)

    def toggle_autoplay(self) -> bool:
        return self._config_manager.toggle_autoplay()

    def set_follow_playback(self, value: bool) -> None:
        self._config_manager.set_follow_playback(value)

    def set_loop_song(self, value: bool) -> None:
        self._config_manager.set_loop_song(value)

    def toggle_favorite(self, path: Path) -> None:
        self._config_manager.toggle_favorite(path)

    def load_current_tab(self) -> Tab:
        return self._state_manager.load_current_tab()

    def set_config_path(self, path: Path) -> None:
        self._state_manager.set_config_path(path)

    def get_config_path(self) -> Path:
        return self._state_manager.get_config_path()

    def set_library_path(self, path: Path) -> None:
        self._state_manager.set_library_path(path)

    def get_library_path(self) -> Path:
        return self._state_manager.get_library_path()

    def set_instrument_path(self, path: Path) -> None:
        self._state_manager.set_instrument_path(path)

    def get_instrument_path(self) -> Path:
        return self._state_manager.get_instrument_path()

    def set_reconstruction_path(self, path: Path) -> None:
        self._state_manager.set_reconstruction_path(path)

    def get_reconstruction_path(self) -> Path:
        return self._state_manager.get_reconstruction_path()

    def set_audio_input_path(self, path: Path) -> None:
        self._state_manager.set_audio_input_path(path)

    def get_audio_input_path(self) -> Path:
        return self._state_manager.get_audio_input_path()

    def set_audio_path(self, path: Path) -> None:
        self._state_manager.set_audio_path(path)

    def get_audio_path(self) -> Path:
        return self._state_manager.get_audio_path()

    def set_project_path(self, path: Path) -> None:
        self._state_manager.set_project_path(path)

    def get_project_path(self) -> Path:
        return self._state_manager.get_project_path()

    def set_current_reconstruction(self, path: Optional[Path]) -> None:
        self._state_manager.set_current_reconstruction(path)

    def set_current_project(self, path: Optional[Path]) -> None:
        self._state_manager.set_current_project(path)

    @property
    def current_project(self) -> Optional[Path]:
        return self._state_manager.current_project

    def set_current_audio_device(
        self,
        audio_device_manager: AudioDeviceManager,
    ) -> None:
        self._config_manager.set_current_audio_device(audio_device_manager)

    def set_master_gain(self, value: float) -> None:
        self._config_manager.set_master_gain(value)

    def set_palette_name(self, name: str) -> None:
        self._config_manager.set_palette_name(name)

    def set_vsync(self, vsync: bool) -> None:
        self._config_manager.set_vsync(vsync)

    def set_max_fps(self, max_fps: int) -> None:
        self._config_manager.set_max_fps(max_fps)

    def set_borderless(self, borderless: bool) -> None:
        self._config_manager.set_borderless(borderless)

    def set_shortcut_scheme_name(self, name: str) -> None:
        self._config_manager.set_shortcut_scheme_name(name)

    def set_shortcut_overrides(
        self,
        overrides: Dict[str, Optional[str]],
    ) -> None:
        self._config_manager.set_shortcut_overrides(overrides)

    def save_config(self) -> None:
        self._config_manager.save()
        self._state_manager.save()

    @property
    def fullscreen(self) -> bool:
        return self._state_manager.fullscreen

    @property
    def window_x(self) -> int:
        return self._state_manager.window_x

    @property
    def window_y(self) -> int:
        return self._state_manager.window_y

    @property
    def window_width(self) -> int:
        return self._state_manager.window_width

    @property
    def window_height(self) -> int:
        return self._state_manager.window_height

    @property
    def current_tab(self) -> str:
        return self._state_manager.current_tab

    @property
    def current_reconstruction(self) -> Optional[Path]:
        return self._state_manager.current_reconstruction

    @property
    def current_audio_device(self) -> CurrentDevice:
        return self._config_manager.current_audio_device

    @property
    def current_buffer_size(self) -> BufferSize:
        return self._config_manager.current_buffer_size

    @property
    def master_gain(self) -> float:
        return self._config_manager.master_gain

    @property
    def palette_name(self) -> str:
        return self._config_manager.palette_name

    @property
    def vsync(self) -> bool:
        return self._config_manager.vsync

    @property
    def max_fps(self) -> int:
        return self._config_manager.max_fps

    @property
    def borderless(self) -> bool:
        return self._config_manager.borderless

    @property
    def shortcut_scheme_name(self) -> str:
        return self._config_manager.shortcut_scheme_name

    @property
    def shortcut_overrides(self) -> Dict[str, Optional[str]]:
        return self._config_manager.shortcut_overrides

    @property
    def advanced_settings(self) -> bool:
        return self._state_manager.advanced_settings

    @property
    def autoplay(self) -> bool:
        return self._config_manager.autoplay

    @property
    def follow_playback(self) -> bool:
        return self._config_manager.follow_playback

    @property
    def loop_song(self) -> bool:
        return self._config_manager.loop_song

    @property
    def favorites(self) -> Set[Path]:
        return self._config_manager.favorites

    @property
    def history_budget(self) -> int:
        return self._config_manager.config.history.budget
