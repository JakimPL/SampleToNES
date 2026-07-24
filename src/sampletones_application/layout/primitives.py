from pydantic import BaseModel


class Dimensions(BaseModel, extra="forbid", frozen=True):
    """A generic width/height pair, in pixels."""

    width: int
    height: int
