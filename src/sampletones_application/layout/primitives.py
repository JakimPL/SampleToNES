from typing import Final, Optional, Tuple

from pydantic import BaseModel, Field

DEARPYGUI_MAXIMUM_WINDOW_SIZE: Final[int] = 30000


class Dimensions(BaseModel, extra="forbid", frozen=True):
    """A generic width/height pair, in pixels."""

    width: int
    height: int


class DialogGeometry(BaseModel, extra="forbid", frozen=True):
    """How large a dialog opens, which is what the place it opens at follows from.

    The width is the dialog's, held both ways: it is the smallest the window may take and the
    largest, so every dialog reads at one width whatever it holds and a field, a combo or a
    button stretching across the window measures against a width that stands. A window free to
    widen to its content and content asking for the window's width feed each other a little
    more every frame, which is what holding the width both ways settles.

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

    @property
    def maximum_size(self) -> Tuple[int, int]:
        """The size the dialog stops at: the width it states, and as tall as what it holds asks for.

        DearPyGui reads a window's bounds as one pair, so a height left to the content is stated
        as the bound DearPyGui carries of its own accord, which is the one no window reaches.
        """
        return self.width, DEARPYGUI_MAXIMUM_WINDOW_SIZE
