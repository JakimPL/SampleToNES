from dataclasses import dataclass
from typing import Iterator


@dataclass
class SongPosition:
    order_position: int = 0
    row_index: int = 0

    def __post_init__(self) -> None:
        if self.order_position < 0:
            raise ValueError(f"order_position must be >= 0, got {self.order_position}")

        if self.row_index < 0:
            raise ValueError(f"row_index must be >= 0, got {self.row_index}")

    def __iter__(self) -> Iterator[int]:
        yield self.order_position
        yield self.row_index

    def advance(self, rows_in_pattern: int, order_length: int) -> None:
        if self.order_position >= order_length:
            return

        self.row_index += 1
        if self.row_index >= rows_in_pattern:
            self.row_index = 0
            self.order_position += 1

    def wrap_overflow(self, rows_in_pattern: int) -> None:
        """Realigns a row that fell outside its pattern to the next frame's first row.

        Shrinking ``rows_per_pattern`` below the active row leaves the playhead beyond
        the pattern's end; playback then resumes at the next frame rather than stalling
        on the now-missing row.
        """
        if self.row_index >= rows_in_pattern:
            self.row_index = 0
            self.order_position += 1
