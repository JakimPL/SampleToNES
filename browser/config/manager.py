from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from configs.config import Config
from configs.general import GeneralConfig
from configs.library import LibraryConfig
from constants.browser import (
    TAG_CONFIG_CHANGE_RATE,
    TAG_CONFIG_MAX_WORKERS,
    TAG_CONFIG_NORMALIZE,
    TAG_CONFIG_QUANTIZE,
    TAG_CONFIG_SAMPLE_RATE,
)
from constants.general import (
    CHANGE_RATE,
    LIBRARY_DIRECTORY,
    MAX_WORKERS,
    NORMALIZE,
    QUANTIZE,
    SAMPLE_RATE,
)
from ffts.window import Window
from library.key import LibraryKey


class ConfigManager:
    def __init__(self) -> None:
        self.config: Optional[Config] = None
        self.window: Optional[Window] = None
        self.library_directory: str = LIBRARY_DIRECTORY
        self.config_change_callbacks: List[Callable] = []
        self.config_params = {
            TAG_CONFIG_NORMALIZE: {"section": "general", "default": NORMALIZE},
            TAG_CONFIG_QUANTIZE: {"section": "general", "default": QUANTIZE},
            TAG_CONFIG_MAX_WORKERS: {"section": "general", "default": MAX_WORKERS},
            TAG_CONFIG_SAMPLE_RATE: {"section": "library", "default": SAMPLE_RATE},
            TAG_CONFIG_CHANGE_RATE: {"section": "library", "default": CHANGE_RATE},
        }

    def update_config_from_gui_values(self, gui_values: Dict[str, Any]) -> None:
        config_data = self._build_config_data_from_values(gui_values)
        self.config = Config(
            general=GeneralConfig(**config_data["general"]),
            library=LibraryConfig(**config_data["library"]),
        )
        self.window = Window(self.config.library)
        self._notify_config_change()

    def _build_config_data_from_values(self, gui_values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        config_data = {"general": {}, "library": {}}

        for tag, info in self.config_params.items():
            section = info["section"]
            value = gui_values.get(tag, info["default"])
            config_data[section][tag] = value

        config_data["general"]["library_directory"] = self.library_directory
        return config_data

    def get_config_preview_data(self) -> Optional[Dict[str, Any]]:
        if not self.config:
            return None

        return {
            "sample_rate": self.config.library.sample_rate,
            "change_rate": self.config.library.change_rate,
            "max_workers": self.config.general.max_workers,
            "normalize": self.config.general.normalize,
            "quantize": self.config.general.quantize,
            "library_directory": Path(self.config.general.library_directory).name,
        }

    def initialize_config_with_defaults(self) -> None:
        default_values = {tag: info["default"] for tag, info in self.config_params.items()}
        self.update_config_from_gui_values(default_values)

    def get_config(self) -> Optional[Config]:
        return self.config

    def get_window(self) -> Optional[Window]:
        return self.window

    @property
    def key(self) -> Optional[LibraryKey]:
        if self.config and self.window:
            return LibraryKey.create(self.config.library, self.window)
        return None

    def set_library_directory(self, directory_path: str) -> None:
        self.library_directory = directory_path

    def add_config_change_callback(self, callback: Callable) -> None:
        self.config_change_callbacks.append(callback)

    def _notify_config_change(self) -> None:
        for callback in self.config_change_callbacks:
            callback()

    def apply_library_config(self, library_key: LibraryKey) -> Dict[str, Any]:
        if not self.config:
            raise ValueError("No config available")

        sample_rate = library_key.sample_rate
        change_rate = round(sample_rate / library_key.frame_length)

        new_library_config = self.config.library.model_copy(
            update={"sample_rate": sample_rate, "change_rate": change_rate}
        )
        new_config = self.config.model_copy(update={"library": new_library_config})

        self.config = new_config
        self.window = Window(self.config.library)

        return {TAG_CONFIG_SAMPLE_RATE: sample_rate, TAG_CONFIG_CHANGE_RATE: change_rate}

    def load_config_from_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        self.config = Config(**config_data)
        self.window = Window(self.config.library)

        gui_updates = {}
        for tag, info in self.config_params.items():
            section = info["section"]
            if section in config_data and tag in config_data[section]:
                gui_updates[tag] = config_data[section][tag]

        if "general" in config_data and "library_directory" in config_data["general"]:
            self.library_directory = config_data["general"]["library_directory"]

        self._notify_config_change()
        return gui_updates
