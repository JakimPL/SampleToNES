from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key import TagName
from sampletones_application.constants.general import SUF_BUTTON

TAG_THEME_GRAPH_INDICATOR = TagName(
    Page.GLOBAL,
    Panel.GRAPH,
    Widget.THEME,
    "indicator",
)
TAG_THEME_GRAPH_ZERO_LINE = TagName(
    Page.GLOBAL,
    Panel.GRAPH,
    Widget.THEME,
    "zero_line",
)
TAG_THEME_GRAPH_OVERLAY = TagName(
    Page.GLOBAL,
    Panel.GRAPH,
    Widget.THEME,
    "overlay",
)

SUF_GRAPH_PLOT = "_plot"
SUF_GRAPH_X_AXIS = "_x_axis"
SUF_GRAPH_Y_AXIS = "_y_axis"
SUF_GRAPH_LEGEND = "_legend"
SUF_GRAPH_CONTROLS = "_controls"
SUF_GRAPH_INFO = "_info"
SUF_GRAPH = "_graph"
SUF_GRAPH_RAW_DATA = "_raw_data"
SUF_GRAPH_RAW_DATA_GROUP = "_raw_data_group"
SUF_GRAPH_THEME = "_theme"
SUF_WAVEFORM_POSITION_INDICATOR = "_position_indicator"
SUF_WAVEFORM_OVERLAY = "_overlay"
SUF_BAR_PLOT_ZERO_LINE = "_zero_line"
SUF_BAR_PLOT_HOVER_BAR = "_hover_bar"
SUF_BAR_PLOT_MOUSE_HANDLER = "_mouse_handler"
SUF_BUTTON_WAVEFORM_RESET_X = f"{SUF_BUTTON}_reset_x"
SUF_BUTTON_WAVEFORM_RESET_Y = f"{SUF_BUTTON}_reset_y"
SUF_BUTTON_WAVEFORM_RESET_ALL = f"{SUF_BUTTON}_reset_all"
