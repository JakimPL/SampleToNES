from pathlib import Path
from typing import Callable, Dict, List, Optional

import dearpygui.dearpygui as dpg

from browser.utils import show_modal_dialog
from configs.config import Config
from configs.general import GeneralConfig
from configs.generation import GenerationConfig
from configs.library import LibraryConfig
from constants.browser import (
    MSG_CONFIG_LOAD_ERROR,
    TAG_CONFIG_CHANGE_RATE,
    TAG_CONFIG_LOAD_ERROR_DIALOG,
    TAG_CONFIG_MAX_WORKERS,
    TAG_CONFIG_NORMALIZE,
    TAG_CONFIG_QUANTIZE,
    TAG_CONFIG_SAMPLE_RATE,
    TAG_RECONSTRUCTOR_MIXER,
    TAG_RECONSTRUCTOR_TRANSFORMATION_GAMMA,
    TITLE_DIALOG_ERROR,
    TPL_RECONSTRUCTION_GEN_TAG,
)
from constants.enums import GeneratorName
from constants.general import (
    CHANGE_RATE,
    CONFIG_PATH,
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
from utils.logger import logger
from utils.serialization import SerializedData, load_json, save_json


class ConfigManager:
    def __init__(self) -> None:
        self.config: Optional[Config] = None
        self.window: Optional[Window] = None
        self.library_directory: Optional[Path] = None
        self.output_directory: Optional[Path] = None
        self.generators: List[GeneratorName] = list(GeneratorName)
        self.config_change_callbacks: List[Callable] = []
        self.config_path: Path = Path(CONFIG_PATH)
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
        self.generator_tags = {
            TPL_RECONSTRUCTION_GEN_TAG.format(generator.value): generator for generator in GeneratorName
        }

        self.initialize()

    def initialize(self) -> None:
        if self.config_path.exists():
            try:
                self.load_config_from_file(self.config_path)
            except Exception as exception:  # TODO: specify exception type
                logger.error_with_traceback(f"Failed to load config from {self.config_path}", exception)
                self._show_config_load_error(str(exception))
                self.load_config(Config())
        else:
            logger.warning(f"Config file does not exist: {self.config_path}")
            self.load_config(Config())

    def _show_config_load_error(self, error_message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_CONFIG_LOAD_ERROR, parent=parent)
            dpg.add_separator(parent=parent)
            dpg.add_text(error_message, wrap=400, parent=parent)

        show_modal_dialog(
            tag=TAG_CONFIG_LOAD_ERROR_DIALOG,
            title=TITLE_DIALOG_ERROR,
            content=content,
        )

    def save_config(self) -> None:
        if not self.config:
            logger.warning("No configuration to save")
            return

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        config_dict = self.config.model_dump()
        save_json(self.config_path, config_dict)

    def update_config_from_gui_values(self, gui_values: SerializedData) -> None:
        self._update_generators_from_gui_values(gui_values)
        config_data = self._build_config_data_from_values(gui_values)
        config_data["generation"]["generators"] = self.generators
        self.config = Config(
            general=GeneralConfig(**config_data["general"]),
            library=LibraryConfig(**config_data["library"]),
            generation=GenerationConfig(**config_data["generation"]),
        )
        self.window = Window(self.config.library)
        self.update_gui()

    def _build_config_data_from_values(self, gui_values: SerializedData) -> Dict[str, SerializedData]:
        config_data = {
            "general": {
                "library_directory": str(self.library_directory),
                "output_directory": str(self.output_directory),
            },
            "library": {},
            "generation": {},
        }

        for data in self.config_parameters.values():
            for tag, info in data.items():
                value = gui_values.get(tag, info["default"])
                section = info["section"]
                config_data[section][tag] = value

        return config_data

    def _update_generators_from_gui_values(self, gui_values: SerializedData) -> None:
        self.generators = [generator for tag, generator in self.generator_tags.items() if gui_values.get(tag, True)]

    def get_config(self) -> Config:
        if self.config is None:
            raise RuntimeError("Config is not loaded")
        return self.config

    def get_window(self) -> Window:
        if self.window is None:
            raise RuntimeError("Window is not loaded")
        return self.window

    def get_library_directory(self) -> Path:
        if self.config is None:
            raise RuntimeError("Config is not loaded")
        return Path(self.config.general.library_directory if self.config else LIBRARY_DIRECTORY)

    def get_output_directory(self) -> Path:
        if self.config is None:
            raise RuntimeError("Config is not loaded")
        return Path(self.config.general.output_directory if self.config else OUTPUT_DIRECTORY)

    @property
    def key(self) -> LibraryKey:
        if not self.config or not self.window:
            raise RuntimeError("Library key is not available")
        return LibraryKey.create(self.config.library, self.window)

    def add_config_change_callback(self, callback: Callable) -> None:
        self.config_change_callbacks.append(callback)

    def update_gui(self) -> None:
        for callback in self.config_change_callbacks:
            callback()

    def apply_library_config(self, library_key: LibraryKey) -> SerializedData:
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

    def load_config_from_data(self, config_data: SerializedData) -> SerializedData:
        self.config = Config(**config_data)
        self.window = Window(self.config.library)
        self.generators = list(self.config.generation.generators)

        gui_updates = {}
        for tag, info in self.config_parameters.items():
            section = info["section"]
            if section in config_data and tag in config_data[section]:
                gui_updates[tag] = config_data[section][tag]

        self.output_directory = config_data["paths"]["output_directory"]
        self.library_directory = config_data["paths"]["library_directory"]

        self.update_gui()
        return gui_updates

    def load_config(self, config: Config) -> None:
        self.config = config
        self.window = Window(self.config.library)
        self.library_directory = Path(config.general.library_directory)
        self.output_directory = Path(config.general.output_directory)
        self.generators = list(config.generation.generators)
        self.update_gui()

    def save_config_to_file(self, filepath: Path) -> None:
        if not self.config:
            raise ValueError("No configuration to save")

        config_dict = self.config.model_dump()
        save_json(filepath, config_dict)

    def load_config_from_file(self, filepath: Path) -> None:
        config_dict = load_json(filepath)
        self.config = Config(**config_dict)
        return self.load_config(self.config)
