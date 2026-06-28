from typing import Final, Optional, Self, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sampletones_core.configs import Config
from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    GAMMA_PREFIX,
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
)
from sampletones_core.constants.enums import (
    GENERATOR_ABBREVIATION_PATTERN,
    GENERATOR_ABBREVIATION_TO_NAME,
    GeneratorName,
    SpectrumMethod,
    abbreviate_generator_names,
)
from sampletones_core.constants.field_aliases import ALIASES
from sampletones_shared.utils.serialization import HASH_PATTERN, hash_models

CONFIG_DIRECTORY_SEPARATOR: Final[str] = "_"


class ConfigDirectoryFields(BaseModel):
    """Structured view of a reconstruction config-directory name.

    The on-disk name is a key-value sequence (``sr_44100_nf_30_sm_fft_tg_0_gn_PTN_ch_<hash>``); the embedded
    keys let :meth:`from_directory_name` validate the name by field. Construction
    (:meth:`from_config`) and parsing live together so the name and its friendly rendering share one
    source of truth. The hash folds in both the library and generation configs, so it disambiguates
    directories whose visible basics coincide.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    sr: int = Field(gt=0, validation_alias=ALIASES["sr"])
    nf: int = Field(gt=0, validation_alias=ALIASES["nf"])
    sm: SpectrumMethod = Field(validation_alias=ALIASES["sm"])
    tg: int = Field(ge=0, validation_alias=ALIASES["tg"])
    gn: str = Field(pattern=GENERATOR_ABBREVIATION_PATTERN, validation_alias=ALIASES["gn"])
    ch: str = Field(pattern=HASH_PATTERN, validation_alias=ALIASES["ch"])

    @property
    def generators(self) -> Tuple[GeneratorName, ...]:
        return tuple(GENERATOR_ABBREVIATION_TO_NAME[character] for character in self.gn)

    @classmethod
    def from_config(cls, config: Config) -> Self:
        return cls(
            sr=config.library.sample_rate,
            nf=config.library.nes_frequency,
            sm=config.library.spectrum_method,
            tg=config.library.transformation_gamma,
            gn=abbreviate_generator_names(config.generation.generators),
            ch=hash_models(config.library, config.generation),
        )

    @classmethod
    def from_directory_name(cls, name: str) -> Optional[Self]:
        """Parses a directory name, returning ``None`` when it is not a config directory.

        Returning ``None`` for non-config names lets callers probe arbitrary filesystem entries
        (plain folders, audio directories) and leave non-matching names untouched. Pydantic validates
        the keys, value types, and hash shape, so a missing or unknown key or a malformed value yields
        ``None``.
        """
        parts = name.split(CONFIG_DIRECTORY_SEPARATOR)
        if len(parts) != 2 * len(cls.model_fields):
            return None

        pairs = dict(zip(parts[::2], parts[1::2]))
        try:
            return cls.model_validate(pairs)
        except ValidationError:
            return None

    @property
    def directory_name(self) -> str:
        pairs = (
            CONFIG_DIRECTORY_SEPARATOR.join(
                [
                    key,
                    str(value),
                ]
            )
            for key, value in self.model_dump().items()
        )
        return CONFIG_DIRECTORY_SEPARATOR.join(pairs)

    @property
    def display_name(self) -> str:
        return DISPLAY_SEPARATOR.join(
            [
                format_sample_rate(self.sr),
                format_nes_frequency(self.nf),
                format_spectrum_method(self.sm),
                f"{GAMMA_PREFIX}{self.tg}",
                self.gn,
            ]
        )

    @classmethod
    def generate_config_directory_name(cls, config: Config) -> str:
        return cls.from_config(config).directory_name
