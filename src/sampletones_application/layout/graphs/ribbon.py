from pydantic import BaseModel


class RibbonLayout(BaseModel, extra="forbid", frozen=True):
    """How the ownership ribbon under the waveform is drawn.

    Attributes:
        lane_height: The height one channel's lane takes.
        padding: The room the ribbon keeps around its lanes.
        lane_gap: The share of a lane left as air beneath it, so the lanes read apart.
    """

    lane_height: int
    padding: int
    lane_gap: float

    def height(self, lanes: int) -> int:
        """The height a ribbon of ``lanes`` lanes is drawn at."""
        return lanes * self.lane_height + self.padding
