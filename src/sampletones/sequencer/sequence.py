from typing import Generic, List

from .typehints import RowT


class Sequence(Generic[RowT]):
    def __init__(self) -> None:
        self.rows: List[RowT] = []

    def __getitem__(self, index: int) -> RowT:
        if isinstance(index, slice):
            return self.rows[index]

        if not isinstance(index, int):
            raise TypeError(f"Index must be an int or slice, got {type(index)}")

        return self.rows[index]

    def __setitem__(self, index: int, value: RowT) -> None:
        self.rows[index] = value

    def __len__(self) -> int:
        return self.length

    @property
    def length(self) -> int:
        return len(self.rows)
