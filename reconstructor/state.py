from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

from instructions.instruction import Instruction


class ReconstructionState(BaseModel):
    fragment_id: int
    fragments: np.ndarray
    instructions: Dict[str, List[Instruction]]
    approximations: Dict[str, List[np.ndarray]] = {}
    current_initials: Dict[str, Tuple[Optional[Any], ...]] = {}
    total_error: float = 0.0

    class Config:
        arbitrary_types_allowed = True
