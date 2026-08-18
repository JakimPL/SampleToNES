import pytest
from pydantic import ValidationError

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.display import (
    DEFAULT_BORDERLESS,
    DEFAULT_MAX_FPS,
    DEFAULT_VSYNC,
    DisplayConfig,
)
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_shared.display import UNLIMITED_FRAME_RATE


class TestDefaults:
    def test_a_fresh_configuration_wears_the_default_palette(self) -> None:
        assert DisplayConfig().palette == DEFAULT_PALETTE_NAME

    def test_a_fresh_configuration_paces_as_shipped(self) -> None:
        display = DisplayConfig()

        assert (display.vsync, display.max_fps, display.borderless) == (
            DEFAULT_VSYNC,
            DEFAULT_MAX_FPS,
            DEFAULT_BORDERLESS,
        )

    def test_the_application_configuration_carries_a_display_section(self) -> None:
        assert ApplicationConfig().display == DisplayConfig()


class TestFrameRate:
    def test_the_unlimited_setting_is_accepted(self) -> None:
        assert DisplayConfig(max_fps=UNLIMITED_FRAME_RATE).max_fps == UNLIMITED_FRAME_RATE

    def test_a_negative_frame_rate_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DisplayConfig(max_fps=-1)


class TestRoundTrip:
    def test_the_settings_survive_a_dump_and_a_reload(self) -> None:
        display = DisplayConfig(
            palette="light",
            vsync=False,
            max_fps=UNLIMITED_FRAME_RATE,
            borderless=True,
        )

        assert DisplayConfig.model_validate(display.model_dump()) == display

    def test_the_settings_survive_the_whole_application_configuration(self) -> None:
        config = ApplicationConfig()
        config.display.palette = "dark"
        config.display.borderless = True

        reloaded = ApplicationConfig.model_validate(config.model_dump())

        assert (reloaded.display.palette, reloaded.display.borderless) == ("dark", True)

    def test_a_configuration_written_before_the_display_section_reads_the_defaults(self) -> None:
        """A stored file outlives the build that wrote it, so an absent section takes defaults."""
        assert ApplicationConfig.model_validate({}).display == DisplayConfig()
