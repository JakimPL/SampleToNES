from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ColumnsLayout(BaseModel, extra="forbid", frozen=True):
    """The shared column skeleton the tab coordinators lay their panels out on.

    ``side`` sizes the uniform left column — the browser, library, or explorer —
    that every tab carries, so the side panel stays the same size across tabs;
    each tab's own right column lives in that tab's section (``<tab>.right_column``).
    A column ``height`` of -1 fills the tab vertically. ``center_weight`` is the
    share of the surplus width the stretching centre column claims against each side
    column's single share as the viewport grows past the responsive baseline (see
    ``ResponsiveLayout`` and ``expanded_side_width``).
    """

    center_weight: int
    side: Dimensions
