from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from configs.config import Config
from configs.general import GeneralConfig
from configs.generation import GenerationConfig
from configs.library import LibraryConfig
from constants.browser import (
    TAG_CONFIG_CHANGE_RATE,
    TAG_CONFIG_MAX_WORKERS,
    TAG_CONFIG_NORMALIZE,
    TAG_CONFIG_QUANTIZE,
    TAG_CONFIG_SAMPLE_RATE,
    TAG_RECONSTRUCTOR_MIXER,
    TAG_RECONSTRUCTOR_TRANSFORMATION_GAMMA,
)
from constants.general import (
    CHANGE_RATE,
    LIBRARY_DIRECTORY,
    MAX_WORKERS,
    MIXER,
    NORMALIZE,
    OUTPUT_DIRECTORY,
    QUANTIZE,
    SAMPLE_RATE,
    TRANSFORMATION_GAMMA,
)
from ffts.window import Window
from library.key import LibraryKey


class ConfigManager:
    def __init__(self) -> None:
        self.config: Optional[Config] = None
        self.window: Optional[Window] = None
        self.library_directory: str = LIBRARY_DIRECTORY
        self.output_directory: str = OUTPUT_DIRECTORY
        self.config_change_callbacks: List[Callable] = []
        self.config_parameters = {
            "config": {
                TAG_CONFIG_NORMALIZE: {"section": "general", "default": NORMALIZE},
                TAG_CONFIG_QUANTIZE: {"section": "general", "default": QUANTIZE},
                TAG_CONFIG_MAX_WORKERS: {"section": "general", "default": MAX_WORKERS},
                TAG_CONFIG_SAMPLE_RATE: {"section": "library", "default": SAMPLE_RATE},
                TAG_CONFIG_CHANGE_RATE: {"section": "library", "default": CHANGE_RATE},
            },
            "reconstructor": {
                TAG_RECONSTRUCTOR_MIXER: {"section": "generation", "default": MIXER},
                TAG_RECONSTRUCTOR_TRANSFORMATION_GAMMA: {"section": "library", "default": TRANSFORMATION_GAMMA},
            },
        }

    def update_config_from_gui_values(self, gui_values: Dict[str, Any]) -> None:
        config_data = self._build_config_data_from_values(gui_values)
        self.config = Config(
            general=GeneralConfig(**config_data["general"]),
            library=LibraryConfig(**config_data["library"]),
            generation=GenerationConfig(**config_data["generation"]),
        )
        self.window = Window(self.config.library)
        self._notify_config_change()

    def _build_config_data_from_values(self, gui_values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        config_data = {
            "general": {"library_directory": self.library_directory, "output_directory": self.output_directory},
            "library": {},
            "generation": {},
        }

        for data in self.config_parameters.values():
            for tag, info in data.items():
                value = gui_values.get(tag, info["default"])
                section = info["section"]
                config_data[section][tag] = value

        return config_data

    def initialize_config_with_defaults(self) -> None:
        default_values = {tag: info["default"] for tag, info in self.config_parameters["config"].items()}
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
        for tag, info in self.config_parameters.items():
            section = info["section"]
            if section in config_data and tag in config_data[section]:
                gui_updates[tag] = config_data[section][tag]

        self.output_directory = config_data["paths"]["output_directory"]
        self.library_directory = config_data["paths"]["library_directory"]

        self._notify_config_change()
        return gui_updates

    def load_config(self, config: Config) -> None:
        self.config = config
        self.window = Window(self.config.library)
        self.library_directory = config.general.library_directory
        self.output_directory = config.general.output_directory
        self._notify_config_change()
