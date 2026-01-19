from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError

from sampletones.configs import Config, GeneralConfig, GenerationConfig, InstructionsLibraryConfig
from sampletones.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones.constants.enums import GeneratorName
from sampletones.constants.general import (
    DEFAULT_CHANGE_RATE,
    MAX_WORKERS,
    MIXER,
    NORMALIZE,
    QUANTIZE,
    TRANSFORMATION_GAMMA,
)
from sampletones.constants.paths import CONFIG_PATH, LIBRARY_DIRECTORY, OUTPUT_DIRECTORY
from sampletones.ffts import Window
from sampletones.library import InstructionLibraryKey
from sampletones.typehints import SerializedData, VoidCallback
from sampletones.utils.logger import logger

from ..config.parameters import ConfigParameter
from ..constants.general import (
    MSG_CONFIGURATION_INVALID_ERROR,
    MSG_CONFIGURATION_LOAD_ERROR,
    MSG_CONFIGURATION_SAVE_ERROR,
)
from ..constants.main import (
    TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE,
    TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE,
    TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS,
    TAG_INPUT_MAIN_CONFIG_CHANGE_RATE,
    TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE,
    TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA,
    TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER,
    TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR,
)
from ..utils.dialogs import show_error_dialog


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config: Config
        self.window: Window

        self.library_directory: Optional[Path] = None
        self.output_directory: Optional[Path] = None
        self.generators: List[GeneratorName] = GeneratorName.items()
        self.config_change_callbacks: List[VoidCallback] = []
        self.config_path: Path = config_path or Path(CONFIG_PATH)
        self.config_parameters: Dict[str, Dict[str, ConfigParameter]] = {
            "config": {
                TAG_CHECKBOX_MAIN_CONFIG_NORMALIZE: ConfigParameter(
                    name="normalize",
                    section="general",
                    default=NORMALIZE,
                ),
                TAG_CHECKBOX_MAIN_CONFIG_QUANTIZE: ConfigParameter(
                    name="quantize",
                    section="general",
                    default=QUANTIZE,
                ),
                TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE: ConfigParameter(
                    name="sample_rate",
                    section="library",
                    default=DEFAULT_SAMPLE_RATE,
                ),
                TAG_INPUT_MAIN_CONFIG_CHANGE_RATE: ConfigParameter(
                    name="change_rate",
                    section="library",
                    default=DEFAULT_CHANGE_RATE,
                ),
                TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA: ConfigParameter(
                    name="transformation_gamma",
                    section="library",
                    default=TRANSFORMATION_GAMMA,
                ),
            },
            "reconstructor": {
                TAG_SLIDER_MAIN_RECONSTRUCTOR_MIXER: ConfigParameter(
                    name="mixer",
                    section="generation",
                    default=MIXER,
                ),
            },
            "advanced": {
                TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS: ConfigParameter(
                    name="max_workers",
                    section="general",
                    default=MAX_WORKERS,
                ),
            },
        }
        self.generator_tags = {
            TPL_TAG_CHECKBOX_MAIN_RECONSTRUCTION_GENERATOR.format(generator.value): generator
            for generator in GeneratorName
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
                show_error_dialog(exception, MSG_CONFIGURATION_LOAD_ERROR)
            except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
                self.load_default_config()
                logger.error_with_traceback(exception, f"File error while loading config from {config_path}")
                show_error_dialog(exception, MSG_CONFIGURATION_LOAD_ERROR)
            except ValidationError as exception:
                self.load_default_config()
                logger.error_with_traceback(exception, f"Invalid config file: {config_path}")
                show_error_dialog(exception, MSG_CONFIGURATION_INVALID_ERROR)
            except Exception as exception:  # TODO: specify exception type
                self.load_default_config()
                logger.error_with_traceback(exception, f"Failed to load config from {config_path}")
                show_error_dialog(exception, MSG_CONFIGURATION_LOAD_ERROR)
        else:
            self.load_default_config()
            logger.warning(f"Config file does not exist: {config_path}")

    def save_config(self) -> None:
        if not self.config:
            logger.warning("No configuration to save")
            return

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config.save(self.config_path)
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"File error while saving config from {self.config_path}")
            show_error_dialog(exception, MSG_CONFIGURATION_SAVE_ERROR)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save config to {self.config_path}")
            show_error_dialog(exception, MSG_CONFIGURATION_SAVE_ERROR)

    def update_config_from_gui_values(self, gui_values: SerializedData) -> None:
        self._update_generators_from_gui_values(gui_values)
        config_data = self._build_config_data_from_values(gui_values)
        config_data["generation"]["generators"] = self.generators

        general_config_data = {**self.config.general.model_dump(), **config_data["general"]}
        library_config_data = {**self.config.library.model_dump(), **config_data["library"]}
        generation_config_data = {**self.config.generation.model_dump(), **config_data["generation"]}
        self.config = Config(
            general=GeneralConfig(**general_config_data),
            library=InstructionsLibraryConfig(**library_config_data),
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

                section = str(info.section)
                config_data[section][info.name] = value

        return config_data

    def _update_generators_from_gui_values(self, gui_values: SerializedData) -> None:
        if any(tag not in gui_values for tag in self.generator_tags.keys()):
            return

        self.generators = [generator for tag, generator in self.generator_tags.items() if gui_values[tag]]

    def get_library_directory(self) -> Path:
        return Path(self.config.general.library_directory if self.config else LIBRARY_DIRECTORY)

    def get_output_directory(self) -> Path:
        return Path(self.config.general.output_directory if self.config else OUTPUT_DIRECTORY)

    @property
    def key(self) -> InstructionLibraryKey:
        return InstructionLibraryKey.create(self.config.library, self.window)

    def add_config_change_callback(self, callback: VoidCallback) -> None:
        self.config_change_callbacks.append(callback)

    def update_gui(self) -> None:
        for callback in self.config_change_callbacks:
            callback()

    def apply_library_config(self, library_key: InstructionLibraryKey) -> SerializedData:
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
            TAG_INPUT_MAIN_CONFIG_SAMPLE_RATE: sample_rate,
            TAG_INPUT_MAIN_CONFIG_CHANGE_RATE: change_rate,
            TAG_INPUT_MAIN_CONFIG_TRANSFORMATION_GAMMA: transformation_gamma,
        }

    def load_default_config(self) -> None:
        self.load_config(Config())

    def load_library_and_generation_config(self, config: Config) -> None:
        self.load_config(
            Config(
                general=self.config.general if self.config else GeneralConfig(),
                library=config.library,
                generation=config.generation,
            )
        )

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
