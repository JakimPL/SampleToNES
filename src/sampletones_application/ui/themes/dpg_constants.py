from typing import Final

import dearpygui.dearpygui as dpg

ITEM_TYPE_MAP: Final[dict[str, int]] = {
    "All": dpg.mvAll,
    "Button": dpg.mvButton,
    "Checkbox": dpg.mvCheckbox,
    "InfLineSeries": dpg.mvInfLineSeries,
    "InputFloat": dpg.mvInputFloat,
    "InputInt": dpg.mvInputInt,
    "InputText": dpg.mvInputText,
    "MenuBar": dpg.mvMenuBar,
    "RadioButton": dpg.mvRadioButton,
    "Selectable": dpg.mvSelectable,
    "ShadeSeries": dpg.mvShadeSeries,
    "Table": dpg.mvTable,
    "Text": dpg.mvText,
    "TreeNode": dpg.mvTreeNode,
}

CORE_COLOR_MAP: Final[dict[str, int]] = {
    "Button": dpg.mvThemeCol_Button,
    "ButtonActive": dpg.mvThemeCol_ButtonActive,
    "ButtonHovered": dpg.mvThemeCol_ButtonHovered,
    "Border": dpg.mvThemeCol_Border,
    "ChildBg": dpg.mvThemeCol_ChildBg,
    "FrameBg": dpg.mvThemeCol_FrameBg,
    "FrameBgActive": dpg.mvThemeCol_FrameBgActive,
    "FrameBgHovered": dpg.mvThemeCol_FrameBgHovered,
    "HeaderActive": dpg.mvThemeCol_HeaderActive,
    "HeaderHovered": dpg.mvThemeCol_HeaderHovered,
    "MenuBarBg": dpg.mvThemeCol_MenuBarBg,
    "PopupBg": dpg.mvThemeCol_PopupBg,
    "TableBorderLight": dpg.mvThemeCol_TableBorderLight,
    "TableBorderStrong": dpg.mvThemeCol_TableBorderStrong,
    "TableHeaderBg": dpg.mvThemeCol_TableHeaderBg,
    "TableRowBg": dpg.mvThemeCol_TableRowBg,
    "TableRowBgAlt": dpg.mvThemeCol_TableRowBgAlt,
    "Text": dpg.mvThemeCol_Text,
    "TextDisabled": dpg.mvThemeCol_TextDisabled,
    "WindowBg": dpg.mvThemeCol_WindowBg,
}

PLOTS_COLOR_MAP: Final[dict[str, int]] = {
    "Fill": dpg.mvPlotCol_Fill,
    "Line": dpg.mvPlotCol_Line,
}

CORE_STYLE_MAP: Final[dict[str, int]] = {
    "ButtonTextAlign": dpg.mvStyleVar_ButtonTextAlign,
    "CellPadding": dpg.mvStyleVar_CellPadding,
    "FrameBorderSize": dpg.mvStyleVar_FrameBorderSize,
    "FramePadding": dpg.mvStyleVar_FramePadding,
    "FrameRounding": dpg.mvStyleVar_FrameRounding,
}

PLOTS_STYLE_MAP: Final[dict[str, int]] = {
    "LineWeight": dpg.mvPlotStyleVar_LineWeight,
}

CATEGORY_MAP: Final[dict[str, int]] = {
    "Core": dpg.mvThemeCat_Core,
    "Plots": dpg.mvThemeCat_Plots,
}
