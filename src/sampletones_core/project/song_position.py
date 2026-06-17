from dataclasses import dataclass
from typing import Iterator


@dataclass
class SongPosition:
    order_position: int = 0
    row_index: int = 0

    def __iter__(self) -> Iterator[int]:
        yield self.order_position
        yield self.row_index

    def advance(self, rows_in_pattern: int, order_length: int) -> None:
        self.row_index += 1
        if self.row_index >= rows_in_pattern:
            self.row_index = 0
            self.order_position = min(self.order_position + 1, order_length)
