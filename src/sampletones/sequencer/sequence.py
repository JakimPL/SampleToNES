from typing import List

from .rows.sample import SampleRow


class Sequence:
    def __init__(self) -> None:
        self.rows: List[SampleRow] = []
