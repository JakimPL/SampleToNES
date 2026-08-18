from pydantic import BaseModel


class ResponsiveLayout(BaseModel, extra="forbid", frozen=True):
    """The design baselines that drive responsive resizing across every tab.

    ``baseline_viewport_width`` and ``baseline_viewport_height`` are the design viewport
    dimensions at which the side columns sit at their configured widths and the stacked
    graphs at their configured heights. Surplus above either baseline is shared out — width
    widens the side columns (``expanded_side_width``), height grows the graph stack
    (``stacked_graph_height``). ``max_graph_height`` is the tallest a single stacked graph
    grows to, from where the surplus is left free.
    """

    baseline_viewport_width: int
    baseline_viewport_height: int
    max_graph_height: int
