from pydantic import BaseModel


class CollapseLayout(BaseModel, extra="forbid", frozen=True):
    """Geometry a collapsed card shrinks to: the header bar for a vertical card, the rail for a docked column."""

    header_bar_height: int
    rail_width: int
    rail_title_gap: int
