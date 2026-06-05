from typing import Optional

from pydantic import BaseModel, ConfigDict

from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_application.view_model.instruction.table_data import InstructionTableData


class InstructionDetailsPanelViewModel(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    instruction_data: Optional[InstructionPanelData]
    table_data: Optional[InstructionTableData]
