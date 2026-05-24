from typing import Tuple

from pydantic import BaseModel, ConfigDict

from ..elements.table.cell import TableCell


class InstructionTableData(BaseModel):
    model_config = ConfigDict(frozen=True)

    general_rows: Tuple[TableCell, ...]
    parameter_rows: Tuple[TableCell, ...]

    @property
    def has_data(self) -> bool:
        return len(self.general_rows) > 0

    @property
    def has_parameters(self) -> bool:
        return len(self.parameter_rows) > 0
