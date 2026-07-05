from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CorpusItem:
    name: str
    category: str
    audio: np.ndarray
