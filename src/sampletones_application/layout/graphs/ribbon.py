from pydantic import BaseModel, Field


class RibbonLayout(BaseModel, extra="forbid", frozen=True):
    """How the ownership ribbon under the waveform is drawn.

    Attributes:
        lane_height: The height one channel's lane takes.
        lane_gap: The share of a lane left as air around its bars, so the lanes read apart.
    """

    lane_height: int = Field(gt=0)
    lane_gap: float = Field(ge=0.0, lt=1.0)
