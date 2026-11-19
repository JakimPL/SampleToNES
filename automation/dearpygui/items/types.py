from typing import Final, Union

Item = Union[int, str]
WINDOW_TYPE: Final[str] = "mvAppItemType::mvWindowAppItem"
CHILD_WINDOW_TYPE: Final[str] = "mvAppItemType::mvChildWindow"
TABLE_TYPE: Final[str] = "mvAppItemType::mvTable"
TREE_NODE_TYPE: Final[str] = "mvAppItemType::mvTreeNode"
MENU_TYPE: Final[str] = "mvAppItemType::mvMenu"
MENU_ITEM_TYPE: Final[str] = "mvAppItemType::mvMenuItem"
TEXT_TYPE: Final[str] = "mvAppItemType::mvText"
BUTTON_TYPE: Final[str] = "mvAppItemType::mvButton"
GROUP_TYPE: Final[str] = "mvAppItemType::mvGroup"
BAR_SERIES_TYPE: Final[str] = "mvAppItemType::mvBarSeries"
LINE_SERIES_TYPE: Final[str] = "mvAppItemType::mvLineSeries"
THEME_COLOR_TYPE: Final[str] = "mvAppItemType::mvThemeColor"
CLICKED_HANDLER_TYPE: Final[str] = "mvAppItemType::mvClickedHandler"
DOUBLE_CLICKED_HANDLER_TYPE: Final[str] = "mvAppItemType::mvDoubleClickedHandler"
HOVER_HANDLER_TYPE: Final[str] = "mvAppItemType::mvHoverHandler"
VISIBLE_HANDLER_TYPE: Final[str] = "mvAppItemType::mvVisibleHandler"
