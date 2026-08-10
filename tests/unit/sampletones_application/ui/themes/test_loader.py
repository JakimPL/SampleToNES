from pathlib import Path
from typing import Dict, Generator, Optional

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.paths import PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DEFAULT
from sampletones_application.ui.themes.loader import ThemeLoader
from sampletones_application.ui.themes.spec import ThemeSpec
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource

_BASE_NAME = "default"

_SYNTHETIC_BASE = """
name: default
tag: synthetic.default
components:
  - item_type: All
    entries:
      - type: color
        key: Text
        value: "#dcdcdcff"
      - type: color
        key: WindowBg
        value: "#242424ff"
  - item_type: Button
    entries:
      - type: color
        key: Button
        value: .reference
  - item_type: Button
    enabled: false
    entries:
      - type: color
        key: Button
        value: "#2e2e3cff"
"""
_SYNTHETIC_PALETTE = """
name: test_palette

colors:
    reference: "#1a1a1a"
"""


def _spec(name: str, *, extends: Optional[str] = None) -> ThemeSpec:
    return ThemeSpec(name=name, tag=f"tag.{name}", extends=extends, components=[])


class TestEffectiveParent:
    def test_a_theme_inherits_the_base_by_default(self) -> None:
        assert ThemeLoader._effective_parent(_spec("converter")) == _BASE_NAME

    def test_the_base_theme_stands_alone(self) -> None:
        assert ThemeLoader._effective_parent(_spec(_BASE_NAME)) is None

    def test_an_explicit_parent_is_respected(self) -> None:
        assert ThemeLoader._effective_parent(_spec("child", extends="table")) == "table"


class TestLoadedInheritance:
    """The real theme set: every theme resolves to the base plus its own overrides,
    so a bound item theme keeps the base's colours instead of dropping to DearPyGui
    defaults for anything it omits.
    """

    @pytest.fixture
    def themes(self) -> Dict[str, Theme]:
        source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
        return {theme.tag: theme for theme in ThemeLoader(THEME_DIRECTORY, source).load_all()}

    def test_every_theme_carries_the_base_table_border(self, themes: Dict[str, Theme]) -> None:
        dpg.create_context()
        try:
            for theme in themes.values():
                theme.create()

            base_border = themes[TAG_GLOBAL_THEME_DEFAULT].get_color(dpg.mvTable, dpg.mvThemeCol_TableBorderStrong)
            assert base_border is not None
            for theme in themes.values():
                assert theme.get_color(dpg.mvTable, dpg.mvThemeCol_TableBorderStrong) == base_border
        finally:
            dpg.destroy_context()

    def test_every_theme_resolves_a_row_background(self, themes: Dict[str, Theme]) -> None:
        dpg.create_context()
        try:
            for theme in themes.values():
                theme.create()

            for theme in themes.values():
                assert theme.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg) is not None
        finally:
            dpg.destroy_context()

    def test_a_theme_keeps_its_own_override_on_top_of_the_base(self, themes: Dict[str, Theme]) -> None:
        dpg.create_context()
        try:
            pattern = themes["sequencer.theme.table_pattern"]
            pattern.create()

            assert pattern.get_style(dpg.mvTable, dpg.mvStyleVar_CellPadding) is not None
            assert pattern.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg) is not None
        finally:
            dpg.destroy_context()

    def test_the_tracker_theme_stands_the_pattern_on_one_even_ground(self, themes: Dict[str, Theme]) -> None:
        """The tracker gives both stripes the same shade, leaving the row background free to
        carry the beat and bar grouping that tells the pattern's rows apart.
        """
        dpg.create_context()
        try:
            base = themes[TAG_GLOBAL_THEME_DEFAULT]
            pattern = themes["sequencer.theme.table_pattern"]
            base.create()
            pattern.create()

            row = pattern.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg)
            assert row == pattern.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBgAlt)
            assert row == base.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg)
        finally:
            dpg.destroy_context()


class TestDisabledStateMirroring:
    """Disabled-state completeness: DearPyGui resolves each item against the theme
    component matching the item's enabled state and re-applies its built-in palette
    when that component is missing, letting the last themed item drawn bleed that
    palette into the global style. A mirrored theme is complete for both states, so
    every item renders with the theme's own values and the global style stays
    intact.
    """

    @pytest.fixture
    def synthetic_theme(self, tmp_path: Path) -> Generator[Theme, None, None]:
        themes_path = tmp_path / "themes"
        themes_path.mkdir(parents=True, exist_ok=True)
        (themes_path / "default.yaml").write_text(_SYNTHETIC_BASE)

        palette_path = tmp_path / "palette.yaml"
        palette_path.write_text(_SYNTHETIC_PALETTE)
        dpg.create_context()
        try:
            theme = ThemeLoader(themes_path, PaletteSource(Palette.load(palette_path))).load_all()[0]
            theme.create()
            yield theme
        finally:
            dpg.destroy_context()

    def test_mirrored_entries_equal_their_enabled_counterparts(self, synthetic_theme: Theme) -> None:
        enabled_background = synthetic_theme.get_color(dpg.mvAll, dpg.mvThemeCol_WindowBg)
        disabled_background = synthetic_theme.get_color(dpg.mvAll, dpg.mvThemeCol_WindowBg, enabled_state=False)
        enabled_text = synthetic_theme.get_color(dpg.mvAll, dpg.mvThemeCol_Text)
        disabled_text = synthetic_theme.get_color(dpg.mvAll, dpg.mvThemeCol_Text, enabled_state=False)

        assert enabled_background is not None
        assert disabled_background == enabled_background
        assert enabled_text is not None
        assert disabled_text == enabled_text

    def test_explicit_disabled_entries_win_over_the_mirror(self, synthetic_theme: Theme) -> None:
        enabled_button = synthetic_theme.get_color(dpg.mvButton, dpg.mvThemeCol_Button)
        disabled_button = synthetic_theme.get_color(dpg.mvButton, dpg.mvThemeCol_Button, enabled_state=False)

        assert enabled_button is not None
        assert disabled_button is not None
        assert disabled_button != enabled_button
