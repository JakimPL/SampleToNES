from pathlib import Path
from typing import Callable, Dict, List, Optional

from sampletones.configs import Config, GeneralConfig, GenerationConfig, LibraryConfig
from sampletones.constants.enums import GeneratorName
from sampletones.constants.general import (
    CHANGE_RATE,
    MAX_WORKERS,
    MIXER,
    NORMALIZE,
    QUANTIZE,
    SAMPLE_RATE,
    TRANSFORMATION_GAMMA,
)
from sampletones.constants.paths import CONFIG_PATH, LIBRARY_DIRECTORY, OUTPUT_DIRECTORY
from sampletones.ffts import Window
from sampletones.library import LibraryKey
from sampletones.typehints import SerializedData
from sampletones.utils import logger, save_json

from ..constants import (
    MSG_CONFIG_LOAD_ERROR,
    MSG_CONFIG_SAVE_ERROR,
    TAG_CONFIG_CHANGE_RATE,
    TAG_CONFIG_MAX_WORKERS,
    TAG_CONFIG_NORMALIZE,
    TAG_CONFIG_QUANTIZE,
    TAG_CONFIG_SAMPLE_RATE,
    TAG_CONFIG_TRANSFORMATION_GAMMA,
    TAG_RECONSTRUCTOR_MIXER,
    TPL_RECONSTRUCTION_GEN_TAG,
)
from ..utils.dialogs import show_error_dialog


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None) -> None:
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
                TAG_CONFIG_TRANSFORMATION_GAMMA: {"section": "library", "default": TRANSFORMATION_GAMMA},
            },
            "reconstructor": {
                TAG_RECONSTRUCTOR_MIXER: {"section": "generation", "default": MIXER},
            },
        }
        self.generator_tags = {
            TPL_RECONSTRUCTION_GEN_TAG.format(generator.value): generator for generator in GeneratorName
        }

        self.initialize(config_path)

    def initialize(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = self.config_path

        if config_path.exists():
            try:
                self.load_config_from_file(config_path)
            except FileNotFoundError as exception:
                self.load_default_config()
                logger.error(f"Config file not found: {config_path}")
                show_error_dialog(exception, MSG_CONFIG_LOAD_ERROR)
            except (IOError, OSError, PermissionError, IsADirectoryError) as exception:
                self.load_default_config()
                logger.error_with_traceback(exception, f"File error while loading config from {config_path}")
                show_error_dialog(exception, MSG_CONFIG_LOAD_ERROR)
            except Exception as exception:  # TODO: specify exception type
                self.load_default_config()
                logger.error_with_traceback(exception, f"Failed to load config from {config_path}")
                show_error_dialog(exception, MSG_CONFIG_LOAD_ERROR)
        else:
            self.load_default_config()
            logger.warning(f"Config file does not exist: {config_path}")

    def save_config(self) -> None:
        if not self.config:
            logger.warning("No configuration to save")
            return

        config_dict = self.config.model_dump()

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            save_json(self.config_path, config_dict)
        except (IOError, OSError, PermissionError, IsADirectoryError) as exception:
            logger.error_with_traceback(exception, f"File error while saving config from {self.config_path}")
            show_error_dialog(exception, MSG_CONFIG_SAVE_ERROR)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save config to {self.config_path}")
            show_error_dialog(exception, MSG_CONFIG_SAVE_ERROR)

    def update_config_from_gui_values(self, gui_values: SerializedData) -> None:
        assert self.config is not None, "Config must be loaded before updating from GUI values"

        self._update_generators_from_gui_values(gui_values)
        config_data = self._build_config_data_from_values(gui_values)
        config_data["generation"]["generators"] = self.generators

        general_config_data = {**self.config.general.model_dump(), **config_data["general"]}
        library_config_data = {**self.config.library.model_dump(), **config_data["library"]}
        generation_config_data = {**self.config.generation.model_dump(), **config_data["generation"]}

        self.config = Config(
            general=GeneralConfig(**general_config_data),
            library=LibraryConfig(**library_config_data),
            generation=GenerationConfig(**generation_config_data),
        )
        self.window = Window.from_config(self.config)
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
                value = gui_values.get(tag)
                if value is None:
                    continue

                section = info["section"]
                config_data[section][tag] = value

        return config_data

    def _update_generators_from_gui_values(self, gui_values: SerializedData) -> None:
        if any(tag not in gui_values for tag in self.generator_tags.keys()):
            return

        self.generators = [generator for tag, generator in self.generator_tags.items() if gui_values[tag]]

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
        window_size = library_key.window_size
        transformation_gamma = library_key.transformation_gamma

        new_library_config = self.config.library.model_copy(
            update={
                "sample_rate": sample_rate,
                "change_rate": change_rate,
                "window_size": window_size,
                "transformation_gamma": transformation_gamma,
            }
        )

        new_config = self.config.model_copy(update={"library": new_library_config})

        self.config = new_config
        self.window = Window.from_config(self.config)

        return {
            TAG_CONFIG_SAMPLE_RATE: sample_rate,
            TAG_CONFIG_CHANGE_RATE: change_rate,
            TAG_CONFIG_TRANSFORMATION_GAMMA: transformation_gamma,
        }

    def load_default_config(self) -> None:
        self.load_config(Config())

    def load_config(self, config: Config) -> None:
        self.config = config
        self.window = Window.from_config(config)
        self.library_directory = Path(config.general.library_directory)
        self.output_directory = Path(config.general.output_directory)
        self.generators = list(config.generation.generators)
        self.update_gui()

    def save_config_to_file(self, filepath: Path) -> None:
        if not self.config:
            raise ValueError("No configuration to save")

        self.config.save(filepath)

    def load_config_from_file(self, filepath: Path) -> None:
        config = Config.load(filepath)
        return self.load_config(config)
