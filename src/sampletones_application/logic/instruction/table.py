from typing import Any, List, Optional, Tuple, Union

from sampletones_application.text.elements.global_ import DialogElements
from sampletones_application.text.elements.instructions import InstructionsDetailsElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.view_model.instruction.cell import TableCell
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_application.view_model.instruction.table_data import InstructionTableData
from sampletones_core.constants.general import DUTY_CYCLES, NOISE_PERIODS
from sampletones_core.utils.frequencies import pitch_to_name
from sampletones_shared.utils.serialization import hash_model


class InstructionTableLogic:
    def __init__(self, *, language_manager: LanguageManager, float_precision: int) -> None:
        self._float_precision = float_precision
        self._lbl_change_rate = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_CHANGE_RATE)
        ]
        self._lbl_generator = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_GENERATOR)
        ]
        self._lbl_frequency = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_FREQUENCY)
        ]
        self._lbl_sample_length = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_SAMPLE_LENGTH)
        ]
        self._lbl_samples = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_SAMPLES_SUFFIX)
        ]
        self._lbl_name = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_NAME)
        ]
        self._lbl_no_frequency = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.LABEL, InstructionsDetailsElements.CELL_NO_FREQUENCY)
        ]
        self._lbl_yes = language_manager[TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.YES)]
        self._lbl_no = language_manager[TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.NO)]
        self._tpl_frequency = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.TEMPLATE, InstructionsDetailsElements.FREQUENCY_TEMPLATE)
        ]
        self._tpl_pitch = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.TEMPLATE, InstructionsDetailsElements.PITCH_TEMPLATE)
        ]
        self._tpl_period = language_manager[
            TextKey(Page.INSTRUCTIONS, Panel.DETAILS, TextType.TEMPLATE, InstructionsDetailsElements.PERIOD_TEMPLATE)
        ]
        self._tpl_duty_cycle = language_manager[
            TextKey(
                Page.INSTRUCTIONS, Panel.DETAILS, TextType.TEMPLATE, InstructionsDetailsElements.DUTY_CYCLE_TEMPLATE
            )
        ]

        self._current_data: Optional[InstructionPanelData] = None
        self._current_hash: str = ""
        self._current_change_rate: Optional[int] = None

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
            rows.append(TableCell(label=self._lbl_change_rate, value=str(self._current_change_rate)))
            rows.append(TableCell(label=self._lbl_generator, value=fragment.generator_class))
            rows.append(
                TableCell(
                    label=self._lbl_frequency,
                    value=self._tpl_frequency.format(fragment.frequency),
                )
            )
            rows.append(
                TableCell(
                    label=self._lbl_sample_length,
                    value=f"{fragment.length}{self._lbl_samples}",
                )
            )
        else:
            rows.append(TableCell(label=self._lbl_generator, value=self.current_data.generator_class_name))
            rows.append(TableCell(label=self._lbl_name, value=self.current_data.instruction.name))
            rows.append(TableCell(label=self._lbl_frequency, value=self._lbl_no_frequency))

        return rows

    def _build_parameter_rows(self) -> List[TableCell]:
        if not self.current_data:
            return []

        rows: List[TableCell] = []
        instruction = self.current_data.instruction

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(field_name, field_value)
            rows.append(TableCell(label=field_name, value=formatted_value))

        return rows

    def _format_parameter_value(
        self,
        name: str,
        value: Union[float, bool, List[Any], Tuple[Any, ...], str, int],
    ) -> str:
        if name == "pitch" and isinstance(value, (int, float)):
            return self._tpl_pitch.format(pitch_to_name(round(value)), value)

        if name == "duty_cycle" and isinstance(value, int):
            duty_cycle = DUTY_CYCLES[value] * 100
            return self._tpl_duty_cycle.format(duty_cycle, value)

        if name == "period" and isinstance(value, int):
            period = NOISE_PERIODS[value]
            return self._tpl_period.format(period, value)

        if isinstance(value, float):
            return f"{value:.{self._float_precision}f}"

        if isinstance(value, bool):
            return self._lbl_yes if value else self._lbl_no

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
            self._current_change_rate = None
            return

        self._current_data = instruction_data
        self._current_hash = hash_model(self._current_data)
        self._current_change_rate = instruction_data.config.change_rate

    @property
    def current_hash(self) -> str:
        return self._current_hash

    @property
    def current_change_rate(self) -> Optional[int]:
        return self._current_change_rate
