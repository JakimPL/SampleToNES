from typing import Protocol

import numpy as np


class Referee(Protocol):
    """Full-reference audio distance: zero for identical signals, growing with audible difference."""

    @property
    def name(self) -> str: ...

    def score(self, reference: np.ndarray, estimate: np.ndarray) -> float: ...
