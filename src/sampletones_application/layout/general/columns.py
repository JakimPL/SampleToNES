from pydantic import BaseModel

from sampletones_application.layout.primitives import Dimensions


class ColumnsLayout(BaseModel, extra="forbid", frozen=True):
    """The fixed-column geometry the tab coordinators lay their panels out on.

    ``side`` sizes the uniform left column — the browser, library, or explorer —
    that every tab carries, so the side panel stays the same size across tabs. Each
    ``*_right`` column sizes one tab's right column, whose width follows the content
    it holds. A column ``height`` of -1 fills the tab vertically.
    ``baseline_viewport_width`` is the design viewport width at which the side columns
    sit at their configured widths; surplus width above it widens the side columns (see
    ``expanded_side_width``). ``center_weight`` is the share of that surplus the
    stretching centre column claims against each side column's single share.
    """

    baseline_viewport_width: int
    center_weight: int
    side: Dimensions
    instructions_right: Dimensions
    reconstructions_right: Dimensions
    sequencer_right: Dimensions
