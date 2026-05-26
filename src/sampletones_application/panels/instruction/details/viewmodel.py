from typing import Optional

from pydantic import BaseModel, ConfigDict

from ....instruction.data import InstructionPanelData
from ....instruction.table import InstructionTableData


class InstructionDetailsPanelViewModel(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    instruction_data: Optional[InstructionPanelData]
    table_data: Optional[InstructionTableData]
