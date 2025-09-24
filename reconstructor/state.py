from typing import List

import numpy as np
from pydantic import BaseModel


class ReconstructionState(BaseModel):
    fragment_id: int
    fragments: np.ndarray
    approximations: List[np.ndarray]

    class Config:
        arbitrary_types_allowed = True
