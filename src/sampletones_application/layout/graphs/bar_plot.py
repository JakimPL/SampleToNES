from pydantic import BaseModel


class BarPlotLayout(BaseModel, extra="forbid", frozen=True):
    """How a dimension's bars are drawn.

    Attributes:
        min_x: Where the first bar's slot begins.
        min_y: The floor of the value range.
        max_y: The ceiling of the value range.
        bar_weight: The share of its slot a bar fills.
        hover_alpha: How solid the bar under the cursor is drawn.
        minimum_span: The slots the axis holds room for, so a short dimension keeps a grid.
        ownership_band: The share of the value range kept beneath it for the stretches naming
            the recording behind each frame.
    """

    min_x: float
    min_y: float
    max_y: float
    bar_weight: float
    hover_alpha: int
    minimum_span: float
    ownership_band: float
