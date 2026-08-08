from typing import Iterator, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.settings import SettingsLayout
from sampletones_application.paths import LANG_EN, LAYOUT_DIRECTORY
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.tags.settings import (
    TAG_SETTINGS_DISPLAY_BUTTON_CANCEL,
    TAG_SETTINGS_DISPLAY_BUTTON_OK,
    TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
    TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN,
    TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC,
    TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
    TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
    TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.dialogs.display_settings import (
    GUIDisplaySettingsWindow,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.shared.display_settings import (
    DisplaySettings,
    DisplaySettingsViewModel,
    WindowMode,
)
from sampletones_shared.display import UNLIMITED_FRAME_RATE, Resolution
from sampletones_shared.utils.serialization import load_yaml_model_dir
from tests.unit.sampletones_application.utils.palette.helpers import build_palette

UNLIMITED_LABEL = "Unlimited"

RESOLUTIONS: Tuple[Resolution, ...] = (
    Resolution(width=1024, height=768),
    Resolution(width=1280, height=800),
    Resolution(width=1600, height=900),
)
FRAME_RATES: Tuple[int, ...] = (UNLIMITED_FRAME_RATE, 30, 60, 120)
PALETTES: Tuple[str, ...] = ("dark", "light", "studio")


def view_model(*, fullscreen: bool = False) -> DisplaySettingsViewModel:
    return DisplaySettingsViewModel(
        settings=DisplaySettings(
            palette="studio",
            window=WindowMode(
                resolution=Resolution(width=1280, height=800),
                borderless=False,
                fullscreen=fullscreen,
            ),
            vsync=True,
            frame_rate=60,
        ),
        resolutions=RESOLUTIONS,
        frame_rates=FRAME_RATES,
        palettes=PALETTES,
    )


@pytest.fixture(name="dpg_context")
def dpg_context_fixture() -> Iterator[None]:
    dpg.create_context()
    FontRegistry.register_fonts()
    ThemeRegistry.register(Theme(tag=TAG_GLOBAL_THEME_DIALOG, items=ThemeItems()))
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


@pytest.fixture(name="window")
def window_fixture(dpg_context: None) -> GUIDisplaySettingsWindow:
    layout = load_yaml_model_dir(
        LAYOUT_DIRECTORY / "settings",
        SettingsLayout,
        context={"palette_source": PaletteSource(build_palette())},
    )
    return GUIDisplaySettingsWindow(
        layout=layout,
        language_manager=LanguageManager(LANG_EN),
        key_router=KeyRouter(),
    )


def render(window: GUIDisplaySettingsWindow, *, fullscreen: bool = False) -> None:
    """Builds the widget tree for the given state, the way ``open`` does without a live frame."""
    window.update_view(view_model(fullscreen=fullscreen))
    window.create_window()


class TestDisplaySettingsWindow:
    def test_every_offered_size_reaches_the_combo(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION)["items"] == [
            "1024x768",
            "1280x800",
            "1600x900",
        ]

    def test_the_selected_size_is_the_one_showing(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert dpg.get_value(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION) == "1280x800"

    def test_the_unlimited_rate_is_offered_by_name(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert UNLIMITED_LABEL in dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE)["items"]

    def test_every_shipped_palette_reaches_the_combo(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_COMBO_PALETTE)["items"] == list(PALETTES)

    def test_the_switches_show_the_state_in_force(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert dpg.get_value(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC) is True
        assert dpg.get_value(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS) is False
        assert dpg.get_value(TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN) is False

    def test_a_windowed_window_offers_its_size_and_frame(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION)["enabled"]
        assert dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS)["enabled"]

    def test_a_fullscreen_window_offers_neither_a_size_nor_a_frame(self, window: GUIDisplaySettingsWindow) -> None:
        render(window, fullscreen=True)

        assert not dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION)["enabled"]
        assert not dpg.get_item_configuration(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS)["enabled"]

    def test_both_actions_are_offered(self, window: GUIDisplaySettingsWindow) -> None:
        render(window)

        assert dpg.does_item_exist(TAG_SETTINGS_DISPLAY_BUTTON_OK)
        assert dpg.does_item_exist(TAG_SETTINGS_DISPLAY_BUTTON_CANCEL)


class TestReportedEdits:
    """Every control reports the whole edited state, so the owner applies one value."""

    @pytest.fixture(name="reported")
    def reported_fixture(self, window: GUIDisplaySettingsWindow) -> List[DisplaySettings]:
        reported: List[DisplaySettings] = []
        window.on_settings_changed = reported.append
        render(window)
        return reported

    def test_picking_a_size_reports_it(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.set_value(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION, "1600x900")
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION)(
            TAG_SETTINGS_DISPLAY_COMBO_RESOLUTION,
            "1600x900",
        )

        assert reported[-1].window.resolution == Resolution(width=1600, height=900)

    def test_switching_borderless_reports_it(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS)(
            TAG_SETTINGS_DISPLAY_CHECKBOX_BORDERLESS,
            True,
        )

        assert reported[-1].window.borderless is True

    def test_switching_fullscreen_reports_it(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN)(
            TAG_SETTINGS_DISPLAY_CHECKBOX_FULLSCREEN,
            True,
        )

        assert reported[-1].window.fullscreen is True

    def test_switching_vsync_reports_it(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC)(
            TAG_SETTINGS_DISPLAY_CHECKBOX_VSYNC,
            False,
        )

        assert reported[-1].vsync is False

    def test_picking_the_unlimited_rate_reports_it(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE)(
            TAG_SETTINGS_DISPLAY_COMBO_FRAME_RATE,
            UNLIMITED_LABEL,
        )

        assert reported[-1].frame_rate == UNLIMITED_FRAME_RATE

    def test_picking_a_palette_reports_it(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_COMBO_PALETTE)(
            TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
            "dark",
        )

        assert reported[-1].palette == "dark"

    def test_an_edit_leaves_the_rest_of_the_state_standing(
        self,
        window: GUIDisplaySettingsWindow,
        reported: List[DisplaySettings],
    ) -> None:
        dpg.get_item_callback(TAG_SETTINGS_DISPLAY_COMBO_PALETTE)(
            TAG_SETTINGS_DISPLAY_COMBO_PALETTE,
            "dark",
        )

        assert reported[-1].vsync is True
        assert reported[-1].window == view_model().settings.window
