from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key import TagName
from sampletones_application.constants.global_ import TAG_SEPARATOR
from sampletones_application.tags.general import SUF_BUTTON

TAG_GLOBAL_GRAPH_THEME_INDICATOR = TagName(
    Page.GLOBAL,
    Panel.GRAPH,
    Widget.THEME,
    "indicator",
)
TAG_GLOBAL_GRAPH_THEME_ZERO_LINE = TagName(
    Page.GLOBAL,
    Panel.GRAPH,
    Widget.THEME,
    "zero_line",
)
TAG_GLOBAL_GRAPH_THEME_OVERLAY = TagName(
    Page.GLOBAL,
    Panel.GRAPH,
    Widget.THEME,
    "overlay",
)

SUF_GRAPH_PLOT = f"{TAG_SEPARATOR}plot"
SUF_GRAPH_X_AXIS = f"{TAG_SEPARATOR}x_axis"
SUF_GRAPH_Y_AXIS = f"{TAG_SEPARATOR}y_axis"
SUF_GRAPH_LEGEND = f"{TAG_SEPARATOR}legend"
SUF_GRAPH_CONTROLS = f"{TAG_SEPARATOR}controls"
SUF_GRAPH_INFO = f"{TAG_SEPARATOR}info"
SUF_GRAPH = f"{TAG_SEPARATOR}graph"
SUF_GRAPH_RAW_DATA = f"{TAG_SEPARATOR}raw_data"
SUF_GROUP_RAW_DATA = f"{TAG_SEPARATOR}group{TAG_SEPARATOR}raw_data"
SUF_GRAPH_THEME = f"{TAG_SEPARATOR}theme"
SUF_WAVEFORM_POSITION_INDICATOR = f"{TAG_SEPARATOR}position_indicator"
SUF_WAVEFORM_OVERLAY = f"{TAG_SEPARATOR}overlay"
SUF_BAR_PLOT_ZERO_LINE = f"{TAG_SEPARATOR}zero_line"
SUF_BAR_PLOT_HOVER_BAR = f"{TAG_SEPARATOR}hover_bar"
SUF_HANDLER_MOUSE = f"{TAG_SEPARATOR}handler{TAG_SEPARATOR}mouse"
SUF_BUTTON_RESET_X = f"{SUF_BUTTON}{TAG_SEPARATOR}reset_x"
SUF_BUTTON_RESET_Y = f"{SUF_BUTTON}{TAG_SEPARATOR}reset_y"
SUF_BUTTON_RESET_ALL = f"{SUF_BUTTON}{TAG_SEPARATOR}reset_all"
