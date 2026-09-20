from typing import Optional, Tuple

from pydantic import BaseModel, Field


class Dimensions(BaseModel, extra="forbid", frozen=True):
    """A generic width/height pair, in pixels."""

    width: int
    height: int


class DialogGeometry(BaseModel, extra="forbid", frozen=True):
    """How large a dialog opens, which is what the place it opens at follows from.

    A dialog states its width, which is what lets a field, a combo or a button stretch across
    it: a stretched item measures one pixel inside the region it is offered, so a window sized
    from its own content would take that pixel back on every frame, and every dialog reads at
    one width whatever it holds.

    The height is the smallest the dialog opens at, and a dialog holding more than that grows
    to hold it, so what a reader is shown is always the whole of what the dialog says. A dialog
    stating a height opens centered on the frame it is first drawn in, since both numbers stand
    before anything is drawn; one stating none is centered against the size it settles at.
    """

    width: int = Field(..., gt=0)
    height: Optional[int] = Field(default=None, gt=0)

    @property
    def minimum_size(self) -> Tuple[int, int]:
        """The size the dialog opens at, which DearPyGui reads as the smallest it may take."""
        return self.width, self.height if self.height is not None else 0
