from typing import Final

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.converter import ConverterConfig
from sampletones_application.constants.output import OutputKind
from sampletones_core.constants.algorithm import ALL_STEMS_CHANNEL_CAP, DEFAULT_STEMS_HIERARCHY_MODE
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings

LOUD_DRIVE: Final[float] = 2.0


class TestDefaults:
    def test_a_fresh_configuration_joins_on_the_usual_channels(self) -> None:
        assert ConverterConfig().settings == StemSettings.covering(list(DEFAULT_CHANNELS))

    def test_a_fresh_configuration_opens_on_the_shipped_run(self) -> None:
        converter = ConverterConfig()

        assert (converter.output, converter.hierarchy_mode) == (
            OutputKind.PER_RECORDING,
            DEFAULT_STEMS_HIERARCHY_MODE,
        )

    def test_the_application_configuration_carries_a_converter_section(self) -> None:
        assert ApplicationConfig().converter == ConverterConfig()


class TestWhatTheFileCarries:
    def test_the_settings_a_recording_joins_with_round_trip(self) -> None:
        """The drives and the count a reader settled are read back on the next launch."""
        settings = StemSettings.covering([ChannelName.PULSE1, ChannelName.NOISE])
        settings = settings.with_drive(ChannelName.PULSE1, LOUD_DRIVE).with_channel_cap(1)

        written = ConverterConfig(settings=settings).model_dump(mode="json")

        assert ConverterConfig.model_validate(written).settings == settings

    def test_a_file_stating_no_drives_reads_them_as_calibrated(self) -> None:
        """A settings file written before drives existed loads as one driving every channel at unit."""
        written = {"settings": {"channels": ["pulse1"], "bends": ["pulse1"]}}

        settings = ConverterConfig.model_validate(written).settings

        assert settings == StemSettings.covering([ChannelName.PULSE1])
        assert settings.channel_cap == ALL_STEMS_CHANNEL_CAP

    def test_a_file_still_naming_a_run_wide_count_loads_without_it(self) -> None:
        written = {"channel_cap": 2, "output": "per_recording"}

        assert ConverterConfig.model_validate(written).settings == ConverterConfig().settings
