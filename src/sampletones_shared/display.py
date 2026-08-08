from typing import Final

from pydantic import BaseModel, Field

UNLIMITED_FRAME_RATE: Final[int] = 0


class Resolution(BaseModel, frozen=True, extra="forbid"):
    """A size in pixels, as a window opens at or a monitor reports."""

    width: int = Field(ge=1)
    height: int = Field(ge=1)

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    def fits_within(self, max_width: int, max_height: int) -> bool:
        """Whether the size stays inside the given bound on both axes."""
        return self.width <= max_width and self.height <= max_height

    def reaches(self, min_width: int, min_height: int) -> bool:
        """Whether the size meets the given minimum on both axes."""
        return self.width >= min_width and self.height >= min_height
