from typing import Any, List, Optional, Tuple, Union

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.view_model.instruction.cell import TableCell
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_application.view_model.instruction.table_data import InstructionTableData
from sampletones_core.constants.general import DUTY_CYCLES, NOISE_PERIODS
from sampletones_core.utils.frequencies import pitch_to_name
from sampletones_shared.utils.serialization import hash_model


class InstructionTableLogic:
    def __init__(
        self,
        *,
        language_manager: LanguageManager,
        float_precision: int,
    ) -> None:
        self._language_manager = language_manager
        self._float_precision = float_precision
        self._lbl_generator = language_manager["instructions.details.label.cell_generator"]
        self._lbl_frequency = language_manager["instructions.details.label.cell_frequency"]

        self._current_data: Optional[InstructionPanelData] = None
        self._current_hash: str = ""
        self._current_nes_frequency: Optional[int] = None

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
                    label=self._language_manager["instructions.details.label.cell_nes_frequency"],
                    value=str(self._current_nes_frequency),
                )
            )
            rows.append(
                TableCell(
                    label=self._lbl_generator,
                    value=fragment.generator_class,
                )
            )
            rows.append(
                TableCell(
                    label=self._lbl_frequency,
                    value=self._language_manager["instructions.details.template.frequency_template"].format(
                        fragment.frequency
                    ),
                )
            )
            samples_suffix = self._language_manager["instructions.details.label.cell_samples_suffix"]
            rows.append(
                TableCell(
                    label=self._language_manager["instructions.details.label.cell_sample_length"],
                    value=f"{fragment.length}{samples_suffix}",
                )
            )
        else:
            rows.append(
                TableCell(
                    label=self._lbl_generator,
                    value=self.current_data.generator_class_name,
                )
            )
            rows.append(
                TableCell(
                    label=self._language_manager["instructions.details.label.cell_name"],
                    value=self.current_data.instruction.name,
                )
            )
            rows.append(
                TableCell(
                    label=self._lbl_frequency,
                    value=self._language_manager["instructions.details.label.cell_no_frequency"],
                )
            )

        return rows

    def _build_parameter_rows(self) -> List[TableCell]:
        if not self.current_data:
            return []

        rows: List[TableCell] = []
        instruction = self.current_data.instruction

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(
                field_name,
                field_value,
            )
            rows.append(TableCell(label=field_name, value=formatted_value))

        return rows

    def _format_parameter_value(
        self,
        name: str,
        value: Union[float, bool, List[Any], Tuple[Any, ...], str, int],
    ) -> str:
        if name == "pitch" and isinstance(value, (int, float)):
            return self._language_manager["instructions.details.template.pitch_template"].format(
                pitch_to_name(round(value)), value
            )

        if name == "duty_cycle" and isinstance(value, int):
            duty_cycle = DUTY_CYCLES[value] * 100
            return self._language_manager["instructions.details.template.duty_cycle_template"].format(duty_cycle, value)

        if name == "period" and isinstance(value, int):
            period = NOISE_PERIODS[value]
            return self._language_manager["instructions.details.template.period_template"].format(period, value)

        if isinstance(value, float):
            return f"{value:.{self._float_precision}f}"

        if isinstance(value, bool):
            return (
                self._language_manager["global.dialog.label.yes"]
                if value
                else self._language_manager["global.dialog.label.no"]
            )

        if isinstance(value, (list, tuple)):
            return f"[{', '.join(str(element) for element in value)}]"

        return str(value)

    @property
    def current_data(self) -> Optional[InstructionPanelData]:
        return self._current_data

    @current_data.setter
    def current_data(
        self,
        instruction_data: Optional[InstructionPanelData],
    ) -> None:
        if instruction_data is None:
            self._current_data = None
            self._current_hash = ""
            self._current_nes_frequency = None
            return

        self._current_data = instruction_data
        self._current_hash = hash_model(self._current_data)
        self._current_nes_frequency = instruction_data.config.nes_frequency

    @property
    def current_hash(self) -> str:
        return self._current_hash

    @property
    def current_nes_frequency(self) -> Optional[int]:
        return self._current_nes_frequency
