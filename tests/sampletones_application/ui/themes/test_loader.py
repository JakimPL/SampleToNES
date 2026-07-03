from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_DEFAULT
from sampletones_application.paths import THEME_DIRECTORY
from sampletones_application.ui.themes.loader import ThemeLoader, _effective_parent
from sampletones_application.ui.themes.spec import ThemeSpec

_BASE_NAME = "default"


def _spec(name: str, *, extends: Optional[str] = None) -> ThemeSpec:
    return ThemeSpec(name=name, tag=f"tag.{name}", extends=extends, components=[])


class TestEffectiveParent:
    def test_a_theme_inherits_the_base_by_default(self) -> None:
        assert _effective_parent(_spec("converter")) == _BASE_NAME

    def test_the_base_theme_stands_alone(self) -> None:
        assert _effective_parent(_spec(_BASE_NAME)) is None

    def test_an_explicit_parent_is_respected(self) -> None:
        assert _effective_parent(_spec("child", extends="table")) == "table"


class TestLoadedInheritance:
    """The real theme set: every theme resolves to the base plus its own overrides,
    so a bound item theme keeps the base's colours instead of dropping to DearPyGui
    defaults for anything it omits.
    """

    def test_every_theme_carries_the_base_row_background(self) -> None:
        dpg.create_context()
        try:
            themes = {theme.tag: theme for theme in ThemeLoader(THEME_DIRECTORY).load_all()}
            for theme in themes.values():
                theme.create()

            base_background = themes[TAG_GLOBAL_THEME_DEFAULT].get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg)
            assert base_background is not None
            for theme in themes.values():
                assert theme.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg) == base_background
        finally:
            dpg.destroy_context()

    def test_a_theme_keeps_its_own_override_on_top_of_the_base(self) -> None:
        dpg.create_context()
        try:
            themes = {theme.tag: theme for theme in ThemeLoader(THEME_DIRECTORY).load_all()}
            pattern = themes["sequencer.theme.table_pattern"]
            pattern.create()

            assert pattern.get_style(dpg.mvTable, dpg.mvStyleVar_CellPadding) is not None
            assert pattern.get_color(dpg.mvTable, dpg.mvThemeCol_TableRowBg) is not None
        finally:
            dpg.destroy_context()
