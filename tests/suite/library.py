from pathlib import Path
from typing import Final, Tuple

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.view_model.main.updates import AdvancedSettingsUpdate
from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.fft.features import get_feature_extractor
from sampletones_core.generators import get_generators_by_channels
from sampletones_core.generators.maps import GENERATOR_TO_INSTRUCTION_MAP
from sampletones_core.library import InstructionLibrary, InstructionLibraryData
from sampletones_core.library.creator.creation import generate_instruction
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_tools.corpus.catalog import CHANNELS, build_mini_library

OTHER_LIBRARIES: Final[str] = "other_libraries"
LINKED_LIBRARIES: Final[str] = "linked_libraries"


class WrittenLibrary:
    """Library data standing in for a generated library, written as an empty library this build
    reads, which is the file the catalog lists."""

    def save(self, path: Path) -> None:
        write_empty_library(path)


def write_empty_library(path: Path) -> None:
    """Writes a library holding no entries at ``path``, stated at the version this build reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    InstructionLibraryData.create(Config(), {}).save(path)


def aim_library_directory(config_manager: ConfigManager, directory: Path) -> None:
    """Points the configuration's library directory at ``directory``, as the advanced settings do."""
    config_manager.apply_advanced_settings(
        AdvancedSettingsUpdate(
            max_workers=config_manager.config.general.max_workers,
            spectrum_method=config_manager.config.library.spectrum_method,
            transformation_gamma=config_manager.config.library.transformation_gamma,
            library_directory=directory,
            reconstructions_directory=config_manager.get_reconstructions_directory(),
        )
    )


def build_served_library(config: Config) -> Tuple[InstructionLibrary, InstructionLibraryKey]:
    """The mini library for ``config``, holding each generator's default instruction beside its samples.

    A converter run matches against any library, while the Instructions tab opens a generator on
    its default instruction, so a library the interface browses holds that one too.

    Returns:
        Tuple[InstructionLibrary, InstructionLibraryKey]: The library, and the key it keeps the data under.
    """
    library = build_mini_library(config)
    window = Window.from_config(config)
    key = library.create_key(config, window)
    extractor = get_feature_extractor(config, window)
    generators = {
        generator.class_name(): generator for generator in get_generators_by_channels(config, CHANNELS).values()
    }
    data = dict(library.data[key].data)
    data.update(
        generate_instruction(
            generators,
            class_name,
            GENERATOR_TO_INSTRUCTION_MAP[type(generator)].default_instruction(),
            extractor,
        )
        for class_name, generator in generators.items()
    )
    library.data[key] = InstructionLibraryData.create(config, data)
    return library, key
