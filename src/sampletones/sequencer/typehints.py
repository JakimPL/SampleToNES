from typing import TypeVar

from .rows.row import Row

RowT = TypeVar("RowT", bound=Row)
