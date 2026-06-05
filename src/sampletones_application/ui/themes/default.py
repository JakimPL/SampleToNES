import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_DEFAULT
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
)
from sampletones_application.ui.themes.theme import Theme


class DefaultTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_DEFAULT
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        c = layout.colors
        b = layout.buttons
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvAll): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=c.text.default,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TextDisabled,
                        color=c.text.disabled,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_WindowBg,
                        color=c.backgrounds.default,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_ChildBg,
                        color=c.backgrounds.default,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_PopupBg,
                        color=c.backgrounds.menu,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_MenuBarBg,
                        color=c.backgrounds.menu,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvMenuBar, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_MenuBarBg,
                        color=c.backgrounds.menu,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Button,
                        color=c.buttons.default,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_ButtonHovered,
                        color=c.buttons.hovered,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_ButtonActive,
                        color=c.buttons.active,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_FrameRounding,
                        x=b.frame_rounding,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_FramePadding,
                        x=b.frame_padding[0],
                        y=b.frame_padding[1],
                    ),
                ],
                ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                    ThemeStyle(
                        key=dpg.mvStyleVar_FrameRounding,
                        x=b.frame_rounding,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_FramePadding,
                        x=b.frame_padding[0],
                        y=b.frame_padding[1],
                    ),
                ],
                ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_TableHeaderBg,
                        color=c.tables.header,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TableRowBg,
                        color=c.tables.row,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TableRowBgAlt,
                        color=c.tables.row_alternative,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TableBorderStrong,
                        color=c.tables.border,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TableBorderLight,
                        color=c.tables.border,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvRadioButton, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=c.text.default,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvRadioButton, enabled_state=False): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=c.text.disabled,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvCheckbox, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=c.text.default,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvCheckbox, enabled_state=False): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=c.text.disabled,
                    ),
                ],
            }
        )
