from typing import Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel

from instructions.instruction import Instruction


class ReconstructionState(BaseModel):
    fragment_id: int
    fragments: np.ndarray
    instructions: Dict[str, List[Instruction]]
    approximations: Dict[str, List[np.ndarray]] = {}
    current_phases: Dict[str, Union[float, int]] = {}
    current_clocks: Dict[str, Optional[float]] = ({},)
    total_error: float = 0.0

    class Config:
        arbitrary_types_allowed = True
