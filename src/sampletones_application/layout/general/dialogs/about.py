from pydantic import BaseModel


class AboutDialogLayout(BaseModel, extra="forbid", frozen=True):
    """The About dialog's size, the size its mark is drawn at, and the room left around the mark."""

    width: int
    height: int
    logo: int
    padding: int

    @property
    def text_wrap(self) -> int:
        """Width the text standing beside the mark wraps at."""
        return self.width - self.logo - self.padding
