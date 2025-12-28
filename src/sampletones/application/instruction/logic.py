from typing import Any, List, Optional, Tuple, Union

from sampletones.constants.general import DUTY_CYCLES, NOISE_PERIODS
from sampletones.utils import hash_model, pitch_to_name

from ..constants.general import LBL_GLOBAL_NO, LBL_GLOBAL_YES
from ..constants.instructions import (
    LBL_CELL_INSTRUCTIONS_DETAILS_DUTY_CYCLE,
    LBL_CELL_INSTRUCTIONS_DETAILS_FREQUENCY,
    LBL_CELL_INSTRUCTIONS_DETAILS_GENERATOR,
    LBL_CELL_INSTRUCTIONS_DETAILS_NAME,
    LBL_CELL_INSTRUCTIONS_DETAILS_NO_FREQUENCY,
    LBL_CELL_INSTRUCTIONS_DETAILS_SAMPLE_LENGTH,
    LBL_CELL_INSTRUCTIONS_DETAILS_SAMPLES,
    TPL_CELL_INSTRUCTIONS_DETAILS_FREQUENCY,
    TPL_CELL_INSTRUCTIONS_DETAILS_PERIOD,
    TPL_CELL_INSTRUCTIONS_DETAILS_PITCH,
    VAL_PRECISION_INSTRUCTIONS_DETAILS_FLOAT,
)
from ..elements.table.cell import TableCell
from .data import InstructionPanelData
from .table import InstructionTableData


class InstructionDetailsLogic:
    def __init__(self) -> None:
        self._current_data: Optional[InstructionPanelData] = None
        self._current_hash: str = ""

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
                    label=LBL_CELL_INSTRUCTIONS_DETAILS_GENERATOR,
                    value=fragment.generator_class,
                )
            )
            rows.append(
                TableCell(
                    label=LBL_CELL_INSTRUCTIONS_DETAILS_FREQUENCY,
                    value=TPL_CELL_INSTRUCTIONS_DETAILS_FREQUENCY.format(fragment.frequency),
                )
            )
            rows.append(
                TableCell(
                    label=LBL_CELL_INSTRUCTIONS_DETAILS_SAMPLE_LENGTH,
                    value=f"{fragment.length}{LBL_CELL_INSTRUCTIONS_DETAILS_SAMPLES}",
                )
            )
        else:
            rows.append(
                TableCell(
                    label=LBL_CELL_INSTRUCTIONS_DETAILS_GENERATOR,
                    value=self.current_data.generator_class_name,
                )
            )
            rows.append(
                TableCell(
                    label=LBL_CELL_INSTRUCTIONS_DETAILS_NAME,
                    value=self.current_data.instruction.name,
                )
            )
            rows.append(
                TableCell(
                    label=LBL_CELL_INSTRUCTIONS_DETAILS_FREQUENCY,
                    value=LBL_CELL_INSTRUCTIONS_DETAILS_NO_FREQUENCY,
                )
            )

        return rows

    def _build_parameter_rows(self) -> List[TableCell]:
        if not self.current_data:
            return []

        rows: List[TableCell] = []
        instruction = self.current_data.instruction

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(field_name, field_value)
            rows.append(
                TableCell(
                    label=field_name,
                    value=formatted_value,
                )
            )

        return rows

    def _format_parameter_value(
        self,
        name: str,
        value: Union[float, bool, List[Any], Tuple[Any, ...], str, int],
    ) -> str:
        if name == "pitch" and isinstance(value, (int, float)):
            return TPL_CELL_INSTRUCTIONS_DETAILS_PITCH.format(pitch_to_name(round(value)), value)

        if name == "duty_cycle" and isinstance(value, int):
            duty_cycle = DUTY_CYCLES[value] * 100
            return LBL_CELL_INSTRUCTIONS_DETAILS_DUTY_CYCLE.format(duty_cycle, value)

        if name == "period" and isinstance(value, int):
            period = NOISE_PERIODS[value]
            return TPL_CELL_INSTRUCTIONS_DETAILS_PERIOD.format(period, value)

        if isinstance(value, float):
            return f"{value:.{VAL_PRECISION_INSTRUCTIONS_DETAILS_FLOAT}f}"

        if isinstance(value, bool):
            return LBL_GLOBAL_YES if value else LBL_GLOBAL_NO

        if isinstance(value, (list, tuple)):
            return f"[{', '.join(str(element) for element in value)}]"

        return str(value)

    @property
    def current_data(self) -> Optional[InstructionPanelData]:
        return self._current_data

    @current_data.setter
    def current_data(self, instruction_data: Optional[InstructionPanelData]) -> None:
        if instruction_data is None:
            self._current_data = None
            self._current_hash = ""
            return

        self._current_data = instruction_data
        self._current_hash = hash_model(self._current_data)

    @property
    def current_hash(self) -> str:
        return self._current_hash
