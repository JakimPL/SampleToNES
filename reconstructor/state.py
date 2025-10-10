from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

from instructions.instruction import Instruction


class ReconstructionState(BaseModel):
    instructions: Dict[str, List[Instruction]]
    approximations: Dict[str, List[np.ndarray]] = {}
    features: Dict[str, List[np.ndarray]] = {}
    current_initials: Dict[str, Optional[Tuple[Any, ...]]] = {}
    total_error: float = 0.0

    @classmethod
    def create(cls, generator_names: List[str]) -> "ReconstructionState":
        return cls(
            instructions={name: [] for name in generator_names},
            approximations={name: [] for name in generator_names},
            features={name: [] for name in generator_names},
            current_initials={name: None for name in generator_names},
            total_error=0.0,
        )

    class Config:
        arbitrary_types_allowed = True
