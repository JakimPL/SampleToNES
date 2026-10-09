from pydantic import BaseModel


class GraphDimensions(BaseModel, extra="forbid", frozen=True):
    """The sizes the plots are drawn at.

    Attributes:
        width: The width a plot fills, negative to take the room it is offered.
        height: The height of a waveform plot.
        bar_plot_height: The height of one dimension's bar plot.
    """

    width: int
    height: int
    bar_plot_height: int
