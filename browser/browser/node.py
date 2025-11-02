from pathlib import Path
from typing import List

from pydantic import BaseModel, ConfigDict


class ReconstructionNode(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str
    path: Path
    is_file: bool
    children: List["ReconstructionNode"] = []
