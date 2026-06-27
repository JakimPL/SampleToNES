from typing import Final, List, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sampletones_core.configs import Config
from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    format_nes_frequency,
    format_sample_rate,
)
from sampletones_core.constants.enums import (
    GENERATOR_ABBREVIATION_TO_NAME,
    GeneratorName,
    abbreviate_generator_names,
)
from sampletones_shared.utils.serialization import HASH_PATTERN, hash_models

CONFIG_DIRECTORY_SEPARATOR: Final[str] = "_"


class ConfigDirectoryFields(BaseModel):
    """Structured view of a reconstruction config-directory name (``sr_nf_gens_hash``).

    Pairs construction (:meth:`from_config`) with parsing (:meth:`from_directory_name`) so the
    on-disk name and its friendly rendering share one source of truth. The hash folds in both the
    library and generation configs, so it disambiguates directories whose visible basics coincide.
    """

    model_config = ConfigDict(frozen=True)

    sample_rate: int = Field(gt=0)
    nes_frequency: int = Field(gt=0)
    generators: List[GeneratorName] = Field(min_length=1)
    config_hash: str = Field(pattern=HASH_PATTERN)

    @classmethod
    def from_config(cls, config: Config) -> Self:
        return cls(
            sample_rate=config.library.sample_rate,
            nes_frequency=config.library.nes_frequency,
            generators=list(config.generation.generators),
            config_hash=hash_models(config.library, config.generation),
        )

    @classmethod
    def from_directory_name(cls, name: str) -> Optional[Self]:
        """Parses a directory name, returning ``None`` when it is not a config directory.

        Returns ``None`` rather than raising so callers can probe arbitrary filesystem entries
        (plain folders, audio directories) and simply leave non-matching names untouched.
        """
        parts = name.split(CONFIG_DIRECTORY_SEPARATOR)
        if len(parts) != len(cls.model_fields):
            return None

        sample_rate, nes_frequency, generators, config_hash = parts
        if not sample_rate.isdigit() or not nes_frequency.isdigit():
            return None

        if not generators or any(character not in GENERATOR_ABBREVIATION_TO_NAME for character in generators):
            return None

        try:
            return cls(
                sample_rate=int(sample_rate),
                nes_frequency=int(nes_frequency),
                generators=[GENERATOR_ABBREVIATION_TO_NAME[character] for character in generators],
                config_hash=config_hash,
            )
        except ValidationError:
            return None

    @property
    def directory_name(self) -> str:
        return CONFIG_DIRECTORY_SEPARATOR.join(
            [
                str(self.sample_rate),
                str(self.nes_frequency),
                abbreviate_generator_names(self.generators),
                self.config_hash,
            ]
        )

    @property
    def display_name(self) -> str:
        return DISPLAY_SEPARATOR.join(
            [
                format_sample_rate(self.sample_rate),
                format_nes_frequency(self.nes_frequency),
                abbreviate_generator_names(self.generators),
            ]
        )

    @classmethod
    def generate_config_directory_name(cls, config: Config) -> str:
        return cls.from_config(config).directory_name
