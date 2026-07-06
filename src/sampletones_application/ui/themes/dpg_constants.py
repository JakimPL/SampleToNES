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
    "Border": dpg.mvThemeCol_Border,
    "Button": dpg.mvThemeCol_Button,
    "ButtonActive": dpg.mvThemeCol_ButtonActive,
    "ButtonHovered": dpg.mvThemeCol_ButtonHovered,
    "CheckMark": dpg.mvThemeCol_CheckMark,
    "ChildBg": dpg.mvThemeCol_ChildBg,
    "FrameBg": dpg.mvThemeCol_FrameBg,
    "FrameBgActive": dpg.mvThemeCol_FrameBgActive,
    "FrameBgHovered": dpg.mvThemeCol_FrameBgHovered,
    "Header": dpg.mvThemeCol_Header,
    "HeaderActive": dpg.mvThemeCol_HeaderActive,
    "HeaderHovered": dpg.mvThemeCol_HeaderHovered,
    "MenuBarBg": dpg.mvThemeCol_MenuBarBg,
    "PopupBg": dpg.mvThemeCol_PopupBg,
    "ScrollbarBg": dpg.mvThemeCol_ScrollbarBg,
    "ScrollbarGrab": dpg.mvThemeCol_ScrollbarGrab,
    "ScrollbarGrabActive": dpg.mvThemeCol_ScrollbarGrabActive,
    "ScrollbarGrabHovered": dpg.mvThemeCol_ScrollbarGrabHovered,
    "Separator": dpg.mvThemeCol_Separator,
    "SeparatorActive": dpg.mvThemeCol_SeparatorActive,
    "SeparatorHovered": dpg.mvThemeCol_SeparatorHovered,
    "SliderGrab": dpg.mvThemeCol_SliderGrab,
    "SliderGrabActive": dpg.mvThemeCol_SliderGrabActive,
    "Tab": dpg.mvThemeCol_Tab,
    "TabActive": dpg.mvThemeCol_TabActive,
    "TabHovered": dpg.mvThemeCol_TabHovered,
    "TableBorderLight": dpg.mvThemeCol_TableBorderLight,
    "TableBorderStrong": dpg.mvThemeCol_TableBorderStrong,
    "TableHeaderBg": dpg.mvThemeCol_TableHeaderBg,
    "TableRowBg": dpg.mvThemeCol_TableRowBg,
    "TableRowBgAlt": dpg.mvThemeCol_TableRowBgAlt,
    "Text": dpg.mvThemeCol_Text,
    "TextDisabled": dpg.mvThemeCol_TextDisabled,
    "TitleBg": dpg.mvThemeCol_TitleBg,
    "TitleBgActive": dpg.mvThemeCol_TitleBgActive,
    "WindowBg": dpg.mvThemeCol_WindowBg,
}

PLOTS_COLOR_MAP: Final[dict[str, int]] = {
    "Fill": dpg.mvPlotCol_Fill,
    "FrameBg": dpg.mvPlotCol_FrameBg,
    "Line": dpg.mvPlotCol_Line,
    "PlotBg": dpg.mvPlotCol_PlotBg,
}

CORE_STYLE_MAP: Final[dict[str, int]] = {
    "ButtonTextAlign": dpg.mvStyleVar_ButtonTextAlign,
    "CellPadding": dpg.mvStyleVar_CellPadding,
    "ChildBorderSize": dpg.mvStyleVar_ChildBorderSize,
    "ChildRounding": dpg.mvStyleVar_ChildRounding,
    "FrameBorderSize": dpg.mvStyleVar_FrameBorderSize,
    "FramePadding": dpg.mvStyleVar_FramePadding,
    "FrameRounding": dpg.mvStyleVar_FrameRounding,
    "GrabMinSize": dpg.mvStyleVar_GrabMinSize,
    "GrabRounding": dpg.mvStyleVar_GrabRounding,
    "IndentSpacing": dpg.mvStyleVar_IndentSpacing,
    "ItemInnerSpacing": dpg.mvStyleVar_ItemInnerSpacing,
    "ItemSpacing": dpg.mvStyleVar_ItemSpacing,
    "PopupRounding": dpg.mvStyleVar_PopupRounding,
    "ScrollbarRounding": dpg.mvStyleVar_ScrollbarRounding,
    "ScrollbarSize": dpg.mvStyleVar_ScrollbarSize,
    "TabRounding": dpg.mvStyleVar_TabRounding,
    "WindowBorderSize": dpg.mvStyleVar_WindowBorderSize,
    "WindowPadding": dpg.mvStyleVar_WindowPadding,
    "WindowRounding": dpg.mvStyleVar_WindowRounding,
}

PLOTS_STYLE_MAP: Final[dict[str, int]] = {
    "LineWeight": dpg.mvPlotStyleVar_LineWeight,
}

CATEGORY_MAP: Final[dict[str, int]] = {
    "Core": dpg.mvThemeCat_Core,
    "Plots": dpg.mvThemeCat_Plots,
}
