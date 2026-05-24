from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    index: int
