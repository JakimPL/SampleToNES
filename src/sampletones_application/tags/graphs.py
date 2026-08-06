from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key.tag import TagName
from sampletones_application.tags.compose import compose_tag

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

SUF_GRAPH_PLOT = "plot"
SUF_GRAPH_X_AXIS = "x_axis"
SUF_GRAPH_Y_AXIS = "y_axis"
SUF_GRAPH_LEGEND = "legend"
SUF_GRAPH_INFO = "info"
SUF_GRAPH = "graph"
SUF_GRAPH_RAW_DATA = "raw_data"
SUF_GRAPH_THEME = "theme"
SUF_WAVEFORM_POSITION_INDICATOR = "position_indicator"
SUF_WAVEFORM_OVERLAY = "overlay"
SUF_BAR_PLOT_ZERO_LINE = "zero_line"
SUF_BAR_PLOT_HOVER_BAR = "hover_bar"
SUF_HANDLER_MOUSE = compose_tag("handler", "mouse")
