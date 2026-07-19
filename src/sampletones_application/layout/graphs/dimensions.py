from pydantic import BaseModel


class GraphDimensions(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int
    bar_plot_height: int
    max_stack_height: int
