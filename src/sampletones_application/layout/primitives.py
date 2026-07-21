from typing import Tuple, TypeAlias

from pydantic import BaseModel

Padding: TypeAlias = Tuple[int, int]


class Dimensions(BaseModel, extra="forbid", frozen=True):
    """A generic width/height pair, in pixels."""

    width: int
    height: int
