from pathlib import Path
from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg

from browser.constants import *
from configs.config import Config
from configs.general import GeneralConfig
from configs.library import LibraryConfig
from constants import (
    CHANGE_RATE,
    LIBRARY_DIRECTORY,
    MAX_WORKERS,
    NORMALIZE,
    QUANTIZE,
    SAMPLE_RATE,
)


class ConfigManager:
    def __init__(self):
        self.config: Optional[Config] = None
        self.library_directory: str = LIBRARY_DIRECTORY
        self.config_params = {
            # General config parameters
            "normalize": {"section": "general", "default": NORMALIZE},
            "quantize": {"section": "general", "default": QUANTIZE},
            "max_workers": {"section": "general", "default": MAX_WORKERS},
            # Library config parameters
            "sample_rate": {"section": "library", "default": SAMPLE_RATE},
            "change_rate": {"section": "library", "default": CHANGE_RATE},
        }

    def register_callbacks(self):
        for tag in self.config_params.keys():
            dpg.set_item_callback(tag, self._on_parameter_change)

    def _on_parameter_change(self, sender, app_data):
        self._update_config()

    def _update_config(self):
        try:
            config_data = self._build_config_data()
            self.config = Config(
                general=GeneralConfig(**config_data["general"]),
                library=LibraryConfig(**config_data["library"]),
            )
            self._update_config_preview()
        except Exception as exception:
            dpg.set_value("config_preview", ERROR_PREFIX.format(f"updating config: {exception}"))

    def _build_config_data(self) -> Dict[str, Dict[str, Any]]:
        config_data = {"general": {}, "library": {}}

        for tag, info in self.config_params.items():
            section = info["section"]
            value = dpg.get_value(tag)
            config_data[section][tag] = value

        config_data["general"]["library_directory"] = self.library_directory
        return config_data

    def _update_config_preview(self):
        if self.config:
            preview_lines = [
                "Configuration updated:",
                f"• Sample rate: {self.config.library.sample_rate} Hz",
                f"• Change rate: {self.config.library.change_rate} fps",
                f"• Max workers: {self.config.general.max_workers}",
                f"• Normalize: {'Yes' if self.config.general.normalize else 'No'}",
                f"• Quantize: {'Yes' if self.config.general.quantize else 'No'}",
                f"• Library: {Path(self.config.general.library_directory).name}",
            ]
            dpg.set_value("config_preview", "\n".join(preview_lines))

    def initialize_config(self):
        self._update_config()

    def get_config(self) -> Optional[Config]:
        return self.config

    def set_library_directory(self, directory_path: str):
        self.library_directory = directory_path
        self._update_config()

    def load_config_from_file(self, config_data: Dict[str, Any]):
        try:
            self.config = Config(**config_data)
            for tag, info in self.config_params.items():
                section = info["section"]
                if section in config_data and tag in config_data[section]:
                    dpg.set_value(tag, config_data[section][tag])

            if "general" in config_data and "library_directory" in config_data["general"]:
                self.library_directory = config_data["general"]["library_directory"]

            self._update_config_preview()
            return True
        except Exception as exception:
            dpg.set_value("config_preview", ERROR_PREFIX.format(f"loading config: {exception}"))
            return False
