from typing import Dict, Final

from sampletones_application.utils.theme.catalog import ThemeEntryAddress
from sampletones_application.utils.theme.spec import CORE_CATEGORY, EVERY_ITEM_TYPE_NAME
from sampletones_tools.web.roles.sources import (
    Axis,
    ColorRole,
    DimensionRole,
    LayoutColorRole,
    LayoutDimensionRole,
    ThemeColorRole,
    ThemeDimensionRole,
)

BASE_THEME: Final[str] = "default"
CHANNEL_ROLE_PREFIX: Final[str] = "channel-"
ENABLED: Final[bool] = True
DISABLED: Final[bool] = False


def channel_role(channel: str) -> str:
    """The role a channel's color stands under, by the channel's name."""
    return f"{CHANNEL_ROLE_PREFIX}{channel}"


def _color(theme: str, item_type: str, key: str, enabled: bool) -> ThemeColorRole:
    return ThemeColorRole(
        theme=theme,
        address=ThemeEntryAddress(item_type=item_type, enabled=enabled, category=CORE_CATEGORY, key=key),
    )


def _style(theme: str, item_type: str, key: str, axis: Axis) -> ThemeDimensionRole:
    return ThemeDimensionRole(
        theme=theme,
        address=ThemeEntryAddress(item_type=item_type, enabled=ENABLED, category=CORE_CATEGORY, key=key),
        axis=axis,
    )


COLOR_ROLES: Final[Dict[str, ColorRole]] = {
    "ground": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "WindowBg", ENABLED),
    "recess": _color("panel_ground", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "surface": _color("panel_surface", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "well": _color("tree_window", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "card-header": _color("collapse_header", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "card-header-hover": _color("collapse_header_hovered", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "heading": _color("section_header", "Text", "Text", ENABLED),
    "emphasis-surface": _color("panel_emphasis", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "emphasis-border": _color("panel_emphasis", EVERY_ITEM_TYPE_NAME, "Border", ENABLED),
    "border": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "Border", ENABLED),
    "separator": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "Separator", ENABLED),
    "text": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "Text", ENABLED),
    "text-muted": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "TextDisabled", ENABLED),
    "text-disabled": _color(BASE_THEME, "Button", "Text", DISABLED),
    "text-strong": _color("table_pattern", EVERY_ITEM_TYPE_NAME, "Text", ENABLED),
    "text-highlight": LayoutColorRole(read=lambda general: general.colors.text.highlight),
    "text-error": LayoutColorRole(read=lambda general: general.colors.text.error),
    "link": LayoutColorRole(read=lambda general: general.colors.paths.default),
    "link-hover": LayoutColorRole(read=lambda general: general.colors.paths.hover),
    "menu": _color(BASE_THEME, "MenuBar", "MenuBarBg", ENABLED),
    "status": _color("status", EVERY_ITEM_TYPE_NAME, "WindowBg", ENABLED),
    "status-text": _color("status", EVERY_ITEM_TYPE_NAME, "Text", ENABLED),
    "tab-strip": _color("tab_strip", EVERY_ITEM_TYPE_NAME, "ChildBg", ENABLED),
    "tab": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "Tab", ENABLED),
    "tab-hover": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "TabHovered", ENABLED),
    "tab-selected": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "TabSelected", ENABLED),
    "button": _color(BASE_THEME, "Button", "Button", ENABLED),
    "button-hover": _color(BASE_THEME, "Button", "ButtonHovered", ENABLED),
    "button-active": _color(BASE_THEME, "Button", "ButtonActive", ENABLED),
    "button-disabled": _color(BASE_THEME, "Button", "Button", DISABLED),
    "secondary": _color("secondary_button", "Button", "Button", ENABLED),
    "secondary-hover": _color("secondary_button", "Button", "ButtonHovered", ENABLED),
    "secondary-active": _color("secondary_button", "Button", "ButtonActive", ENABLED),
    "secondary-text": _color("secondary_button", "Button", "Text", ENABLED),
    "secondary-border": _color("secondary_button", "Button", "Border", ENABLED),
    "focus": _color("focused_button", "Button", "Border", ENABLED),
    "table-header": _color(BASE_THEME, "Table", "TableHeaderBg", ENABLED),
    "table-row": _color(BASE_THEME, "Table", "TableRowBg", ENABLED),
    "table-row-alt": _color(BASE_THEME, "Table", "TableRowBgAlt", ENABLED),
    "table-border": _color(BASE_THEME, "Table", "TableBorderStrong", ENABLED),
    "selection": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "Header", ENABLED),
    "block-selection": _color("table_pattern", "Selectable", "Header", ENABLED),
    "scrollbar-track": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "ScrollbarBg", ENABLED),
    "scrollbar-grab": _color(BASE_THEME, EVERY_ITEM_TYPE_NAME, "ScrollbarGrab", ENABLED),
    channel_role("pulse1"): LayoutColorRole(read=lambda general: general.colors.channels.pulse1),
    channel_role("pulse2"): LayoutColorRole(read=lambda general: general.colors.channels.pulse2),
    channel_role("triangle"): LayoutColorRole(read=lambda general: general.colors.channels.triangle),
    channel_role("noise"): LayoutColorRole(read=lambda general: general.colors.channels.noise),
}

DIMENSION_ROLES: Final[Dict[str, DimensionRole]] = {
    "card-radius": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "ChildRounding", Axis.X),
    "card-border": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "ChildBorderSize", Axis.X),
    "card-padding-x": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "WindowPadding", Axis.X),
    "card-padding-y": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "WindowPadding", Axis.Y),
    "frame-radius": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "FrameRounding", Axis.X),
    "tab-radius": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "TabRounding", Axis.X),
    "item-spacing-x": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "ItemSpacing", Axis.X),
    "item-spacing-y": _style(BASE_THEME, EVERY_ITEM_TYPE_NAME, "ItemSpacing", Axis.Y),
    "button-padding-x": _style(BASE_THEME, "Button", "FramePadding", Axis.X),
    "button-padding-y": _style(BASE_THEME, "Button", "FramePadding", Axis.Y),
    "menu-padding-x": _style(BASE_THEME, "MenuBar", "FramePadding", Axis.X),
    "cell-padding-x": _style("table", "Table", "CellPadding", Axis.X),
    "cell-padding-y": _style("table", "Table", "CellPadding", Axis.Y),
    "header-height": LayoutDimensionRole(read=lambda general: general.collapse.header_bar_height),
    "glyph-indent": LayoutDimensionRole(read=lambda general: general.section_header.glyph.indent),
    "glyph-width": LayoutDimensionRole(read=lambda general: general.section_header.glyph.width),
    "glyph-top": LayoutDimensionRole(read=lambda general: general.section_header.glyph.top_offset),
    "chevron-offset": LayoutDimensionRole(read=lambda general: general.section_header.chevron_offset),
    "panel-gap": LayoutDimensionRole(read=lambda general: general.panel_gap),
    "side-column": LayoutDimensionRole(read=lambda general: general.columns.side.width),
    "status-height": LayoutDimensionRole(read=lambda general: general.status_bar.height),
}
