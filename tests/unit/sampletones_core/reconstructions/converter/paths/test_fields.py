import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.display import (
    DISPLAY_SEPARATOR,
    GAMMA_PREFIX,
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
)
from sampletones_core.constants.enums import GeneratorName, abbreviate_generator_names
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields

HASH = "6edf7c948606917a78b45d153c7ca7e0"


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


class TestGenerateConfigDirectoryName:
    def test_result_contains_sample_rate(self, config: Config) -> None:
        name = ConfigDirectoryFields.generate_config_directory_name(config)
        assert str(config.library.sample_rate) in name

    def test_result_contains_nes_frequency(self, config: Config) -> None:
        name = ConfigDirectoryFields.generate_config_directory_name(config)
        assert str(config.library.nes_frequency) in name

    def test_same_config_produces_same_name(self, config: Config) -> None:
        assert ConfigDirectoryFields.generate_config_directory_name(
            config
        ) == ConfigDirectoryFields.generate_config_directory_name(config)

    def test_different_generator_sets_produce_different_names(self, config: Config) -> None:
        single_generator_config = config.model_copy(
            update={"generation": config.generation.model_copy(update={"generators": [GeneratorName.PULSE1]})}
        )

        assert ConfigDirectoryFields.generate_config_directory_name(
            config
        ) != ConfigDirectoryFields.generate_config_directory_name(single_generator_config)


class TestConfigDirectoryFields:
    def test_round_trips_with_generate_config_directory_name(self, config: Config) -> None:
        name = ConfigDirectoryFields.generate_config_directory_name(config)
        fields = ConfigDirectoryFields.from_directory_name(name)
        assert fields is not None
        assert fields.directory_name == name

    def test_parses_components(self, config: Config) -> None:
        name = ConfigDirectoryFields.generate_config_directory_name(config)
        fields = ConfigDirectoryFields.from_directory_name(name)
        assert fields is not None
        assert fields.sr == config.library.sample_rate
        assert fields.nf == config.library.nes_frequency
        assert fields.sm == config.library.spectrum_method
        assert fields.tg == config.library.transformation_gamma
        assert fields.generators == tuple(config.generation.generators)

    def test_directory_name_embeds_field_keys(self, config: Config) -> None:
        name = ConfigDirectoryFields.generate_config_directory_name(config)
        segments = name.split("_")
        assert {"sr", "nf", "sm", "tg", "gn", "ch"}.issubset(segments)

    @pytest.mark.parametrize(
        "name",
        [
            "not-a-config-dir",
            "sr_44100_nf_30_gn_PTN",
            f"xx_44100_nf_30_sm_fft_tg_0_gn_PTN_ch_{HASH}",
            f"sr_notanumber_nf_30_sm_fft_tg_0_gn_PTN_ch_{HASH}",
            f"sr_44100_nf_30_sm_xyz_tg_0_gn_PTN_ch_{HASH}",
            f"sr_44100_nf_30_sm_fft_tg_-1_gn_PTN_ch_{HASH}",
            f"sr_44100_nf_30_sm_fft_tg_0_gn_XYZ_ch_{HASH}",
            f"sr_44100_nf_30_sm_fft_tg_0_gn__ch_{HASH}",
            "sr_44100_nf_30_sm_fft_tg_0_gn_PTN_ch_short",
        ],
    )
    def test_malformed_names_return_none(self, name: str) -> None:
        assert ConfigDirectoryFields.from_directory_name(name) is None

    def test_display_name_combines_formatted_parts(self, config: Config) -> None:
        fields = ConfigDirectoryFields.from_config(config)
        display = fields.display_name

        assert format_sample_rate(config.library.sample_rate) in display
        assert format_nes_frequency(config.library.nes_frequency) in display
        assert format_spectrum_method(config.library.spectrum_method) in display
        assert f"{GAMMA_PREFIX}{config.library.transformation_gamma}" in display
        assert abbreviate_generator_names(list(config.generation.generators)) in display
        assert DISPLAY_SEPARATOR in display
