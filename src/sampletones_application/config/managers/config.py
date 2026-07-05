import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from sampletones_application.config.managers.outcome import (
    ConfigLoadFailure,
    ConfigLoadFailureReason,
    ConfigLoadOutcome,
    ConfigRecovered,
)
from sampletones_application.view_model.main.updates import (
    AdvancedSettingsUpdate,
    AudioSettingsUpdate,
    GenerationSettingsUpdate,
    LibrarySettingsUpdate,
)
from sampletones_core.configs import Config
from sampletones_core.data.metadata import Metadata
from sampletones_core.fft import Window
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.paths import CONFIG_PATH, LIBRARY_DIRECTORY
from sampletones_shared.constants.project import RECONSTRUCTIONS_DIRECTORY
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.serialization import load_json
from sampletones_shared.utils.validation import validate_with_recovery


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config: Config
        self.window: Window

        self.library_directory: Optional[Path] = None
        self.reconstructions_directory: Optional[Path] = None
        self.config_change_callbacks: List[VoidCallback] = []
        self.config_path: Path = config_path or Path(CONFIG_PATH)
        self.pending_load_outcomes: List[ConfigLoadOutcome] = []

        self.initialize(config_path)

    def initialize(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = self.config_path

        if not config_path.exists():
            self.load_default_config()
            logger.warning(f"Config file does not exist: {config_path}")
            return

        try:
            self.load_config_from_file(config_path)
        except FileNotFoundError as exception:
            self.load_default_config()
            logger.error(f"Config file not found: {config_path}")
            self.pending_load_outcomes.append(ConfigLoadFailure(exception, ConfigLoadFailureReason.LOAD_ERROR))
        except OSError as exception:
            self.load_default_config()
            logger.error_with_traceback(
                exception,
                f"File error while loading config from {config_path}",
            )
            self.pending_load_outcomes.append(ConfigLoadFailure(exception, ConfigLoadFailureReason.LOAD_ERROR))
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exception:
            self.load_default_config()
            logger.error_with_traceback(exception, f"Unreadable config file: {config_path}")
            self.pending_load_outcomes.append(ConfigLoadFailure(exception, ConfigLoadFailureReason.PARSE_ERROR))
        except ValidationError as exception:
            self.load_default_config()
            logger.error_with_traceback(exception, f"Invalid config file: {config_path}")
            self.pending_load_outcomes.append(ConfigLoadFailure(exception, ConfigLoadFailureReason.INVALID))

    def save_config(self) -> None:
        if not self.config:
            logger.warning("No configuration to save")
            return

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.save(self.config_path)

    def apply_audio_settings(self, update: AudioSettingsUpdate) -> None:
        new_general = self.config.general.model_copy(
            update={
                "normalize": update.normalize,
                "quantize": update.quantize,
            }
        )
        self.config = self.config.model_copy(update={"general": new_general})
        self.window = Window.from_config(self.config)
        self.update_gui()

    def apply_library_settings(self, update: LibrarySettingsUpdate) -> None:
        new_library = self.config.library.model_copy(
            update={
                "sample_rate": update.sample_rate,
                "nes_frequency": update.nes_frequency,
                "spectrum_method": update.spectrum_method,
                "transformation_gamma": update.transformation_gamma,
            }
        )
        self.config = self.config.model_copy(update={"library": new_library})
        self.window = Window.from_config(self.config)
        self.update_gui()

    def apply_generation_settings(self, update: GenerationSettingsUpdate) -> None:
        new_generation = self.config.generation.model_copy(
            update={
                "drive": update.drive,
                "generators": update.generators,
            }
        )
        self.config = self.config.model_copy(
            update={
                "generation": new_generation,
            }
        )
        self.window = Window.from_config(self.config)
        self.update_gui()

    def apply_advanced_settings(self, update: AdvancedSettingsUpdate) -> None:
        new_general = self.config.general.model_copy(
            update={
                "max_workers": update.max_workers,
                "library_directory": str(update.library_directory),
                "reconstructions_directory": str(update.reconstructions_directory),
            }
        )
        self.config = self.config.model_copy(update={"general": new_general})
        self.window = Window.from_config(self.config)
        self.library_directory = update.library_directory
        self.reconstructions_directory = update.reconstructions_directory
        self.update_gui()

    def get_library_directory(self) -> Path:
        return Path(self.config.general.library_directory if self.config else LIBRARY_DIRECTORY)

    def get_reconstructions_directory(self) -> Path:
        return Path(self.config.general.reconstructions_directory if self.config else RECONSTRUCTIONS_DIRECTORY)

    @property
    def key(self) -> InstructionLibraryKey:
        return InstructionLibraryKey.create(self.config.library, self.window)

    def add_config_change_callback(self, callback: VoidCallback) -> None:
        self.config_change_callbacks.append(callback)

    def update_gui(self) -> None:
        for callback in self.config_change_callbacks:
            callback()

    def apply_library_config(self, library_key: InstructionLibraryKey) -> None:
        sample_rate = library_key.sample_rate
        nes_frequency = round(sample_rate / library_key.frame_length)
        window_size = library_key.window_size
        transformation_gamma = library_key.transformation_gamma
        spectrum_method = library_key.spectrum_method

        new_library_config = self.config.library.model_copy(
            update={
                "sample_rate": sample_rate,
                "nes_frequency": nes_frequency,
                "window_size": window_size,
                "spectrum_method": spectrum_method,
                "transformation_gamma": transformation_gamma,
            }
        )

        self.config = self.config.model_copy(update={"library": new_library_config})
        self.window = Window.from_config(self.config)
        self.update_gui()

    def load_default_config(self) -> None:
        self.load_config(Config())

    def load_config(self, config: Config) -> None:
        self.config = config
        self.window = Window.from_config(config)
        self.library_directory = Path(config.general.library_directory)
        self.reconstructions_directory = Path(config.general.reconstructions_directory)
        self.update_gui()

    def save_config_to_file(self, filepath: Path) -> None:
        if not self.config:
            raise ValueError("No configuration to save")

        self.config.save(filepath)

    def load_config_from_file(self, filepath: Path) -> None:
        raw = load_json(filepath)
        if not isinstance(raw, dict):
            raise TypeError(f"Expected config file to contain a dict, got {type(raw)}")

        old_version = self._extract_version(raw)
        recovered = validate_with_recovery(Config, raw)
        config = recovered.model.model_copy(update={"metadata": Metadata.default()})
        self.load_config(config)

        if recovered.dropped:
            self.pending_load_outcomes.append(
                ConfigRecovered(
                    source_version=old_version,
                    dropped=recovered.dropped,
                )
            )

    @staticmethod
    def _extract_version(raw: Dict[str, Any]) -> Optional[str]:
        try:
            version = raw["metadata"]["version"]
        except KeyError:
            return None

        return version if isinstance(version, str) else None
