from typing import Any, List, Optional, Tuple, Union

from sampletones.instructions import InstructionUnion
from sampletones.library import InstructionLibraryFragment
from sampletones.utils import hash_model

from ..constants import (
    FMT_INSTRUCTION_FREQUENCY,
    LBL_GLOBAL_NO,
    LBL_GLOBAL_YES,
    LBL_INSTRUCTION_FREQUENCY,
    LBL_INSTRUCTION_GENERATOR,
    LBL_INSTRUCTION_NAME,
    LBL_INSTRUCTION_SAMPLE_LENGTH,
    MSG_INSTRUCTION_NO_FREQUENCY,
    SUF_INSTRUCTION_SAMPLE_LENGTH,
    VAL_INSTRUCTION_FLOAT_PRECISION,
)
from ..elements.table.cell import TableCell
from .data import InstructionPanelData
from .table import InstructionTableData


class InstructionDetailsLogic:
    def __init__(self) -> None:
        self.current_data: Optional[InstructionPanelData] = None
        self.current_hash: str = ""

    def set_instruction_data(
        self,
        generator_class_name: str,
        instruction: InstructionUnion,
        fragment: Optional[InstructionLibraryFragment[Any]] = None,
    ) -> InstructionPanelData:
        self.current_data = InstructionPanelData(
            generator_class_name=generator_class_name,
            instruction=instruction,
            fragment=fragment,
        )
        self.current_hash = hash_model(self.current_data)
        return self.current_data

    def clear_data(self) -> None:
        self.current_data = None

    def get_table_data(self) -> Optional[InstructionTableData]:
        if not self.current_data:
            return None

        general_rows = self._build_general_rows()
        parameter_rows = self._build_parameter_rows()

        return InstructionTableData(
            general_rows=tuple(general_rows),
            parameter_rows=tuple(parameter_rows),
        )

    def _build_general_rows(self) -> List[TableCell]:
        if not self.current_data:
            return []

        rows: List[TableCell] = []

        if self.current_data.fragment:
            fragment = self.current_data.fragment
            rows.append(
                TableCell(
                    label=LBL_INSTRUCTION_GENERATOR,
                    value=fragment.generator_class,
                )
            )
            rows.append(
                TableCell(
                    label=LBL_INSTRUCTION_FREQUENCY,
                    value=FMT_INSTRUCTION_FREQUENCY.format(fragment.frequency),
                )
            )
            rows.append(
                TableCell(
                    label=LBL_INSTRUCTION_SAMPLE_LENGTH,
                    value=f"{fragment.length}{SUF_INSTRUCTION_SAMPLE_LENGTH}",
                )
            )
        else:
            rows.append(
                TableCell(
                    label=LBL_INSTRUCTION_GENERATOR,
                    value=self.current_data.generator_class_name,
                )
            )
            rows.append(
                TableCell(
                    label=LBL_INSTRUCTION_NAME,
                    value=self.current_data.instruction.name,
                )
            )
            rows.append(
                TableCell(
                    label=LBL_INSTRUCTION_FREQUENCY,
                    value=MSG_INSTRUCTION_NO_FREQUENCY,
                )
            )

        return rows

    def _build_parameter_rows(self) -> List[TableCell]:
        if not self.current_data:
            return []

        rows: List[TableCell] = []
        instruction = self.current_data.instruction

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(field_value)
            rows.append(
                TableCell(
                    label=field_name,
                    value=formatted_value,
                )
            )

        return rows

    def _format_parameter_value(self, value: Union[float, bool, List[Any], Tuple[Any, ...], str, int]) -> str:
        if isinstance(value, float):
            return f"{value:.{VAL_INSTRUCTION_FLOAT_PRECISION}f}"

        if isinstance(value, bool):
            return LBL_GLOBAL_YES if value else LBL_GLOBAL_NO

        if isinstance(value, (list, tuple)):
            return f"[{', '.join(str(v) for v in value)}]"

        return str(value)
