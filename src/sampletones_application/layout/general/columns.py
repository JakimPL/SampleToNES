from pydantic import BaseModel


class ColumnLayout(BaseModel, extra="forbid", frozen=True):
    """Dimensions of one fixed column in a tab layout; a ``height`` of -1 fills the tab vertically."""

    width: int
    height: int


class ColumnsLayout(BaseModel, extra="forbid", frozen=True):
    """The fixed-column geometry the tab coordinators lay their panels out on.

    ``side`` sizes the uniform left column — the browser, library, or explorer —
    that every tab carries, so the side panel stays the same size across tabs. Each
    ``*_right`` column sizes one tab's right column, whose width follows the content
    it holds. ``baseline_viewport_width`` is the design viewport width at which the
    side columns sit at their configured widths; surplus width above it widens the
    side columns (see ``expanded_side_width``). ``center_weight`` is the share of that
    surplus the stretching centre column claims against each side column's single share.
    """

    baseline_viewport_width: int
    center_weight: int
    side: ColumnLayout
    instructions_right: ColumnLayout
    reconstructions_right: ColumnLayout
    sequencer_right: ColumnLayout
