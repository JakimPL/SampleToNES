from typing import Dict, List

import numpy as np
from pydantic import BaseModel

from instructions.instruction import Instruction


class ReconstructionState(BaseModel):
    fragment_id: int
    fragments: np.ndarray
    instructions: Dict[str, List[Instruction]]
    approximations: List[np.ndarray]
    partial_approximations: Dict[str, List[np.ndarray]] = {}
    total_error: float = 0.0

    class Config:
        arbitrary_types_allowed = True
