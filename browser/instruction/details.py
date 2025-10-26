from typing import Optional, Union

import dearpygui.dearpygui as dpg

from browser.constants import (
    FMT_INSTRUCTION_FREQUENCY,
    LBL_GLOBAL_NO,
    LBL_GLOBAL_YES,
    LBL_INSTRUCTION_PARAMETERS_HEADER,
    MSG_INSTRUCTION_DETAILS,
    MSG_INSTRUCTION_NO_FREQUENCY,
    MSG_INSTRUCTION_NO_SELECTION,
    PFX_INSTRUCTION_FREQUENCY,
    PFX_INSTRUCTION_GENERATOR,
    PFX_INSTRUCTION_NAME,
    PFX_INSTRUCTION_OFFSET,
    PFX_INSTRUCTION_PARAMETER_INDENT,
    PFX_INSTRUCTION_SAMPLE_LENGTH,
    SUF_INSTRUCTION_SAMPLE_LENGTH,
    VAL_INSTRUCTION_FLOAT_PRECISION,
)
from browser.instruction.data import InstructionPanelData
from library.data import LibraryFragment
from typehints.instructions import InstructionUnion


class InstructionDetailsLogic:
    def __init__(self) -> None:
        self.current_data: Optional[InstructionPanelData] = None

    def set_instruction_data(
        self, generator_class_name: str, instruction: InstructionUnion, fragment: Optional[LibraryFragment] = None
    ) -> InstructionPanelData:
        self.current_data = InstructionPanelData(
            generator_class_name=generator_class_name, instruction=instruction, fragment=fragment
        )
        return self.current_data

    def clear_data(self) -> None:
        self.current_data = None

    def get_display_text(self) -> str:
        if not self.current_data:
            return MSG_INSTRUCTION_NO_SELECTION

        if not self.current_data.fragment:
            lines = [
                f"{PFX_INSTRUCTION_GENERATOR}{self.current_data.generator_class_name}",
                f"{PFX_INSTRUCTION_NAME}{self.current_data.instruction.name}",
                f"{PFX_INSTRUCTION_FREQUENCY}{MSG_INSTRUCTION_NO_FREQUENCY}",
            ]
            return "\n".join(lines)

        fragment = self.current_data.fragment
        instruction = self.current_data.instruction

        lines = [
            f"{PFX_INSTRUCTION_GENERATOR}{fragment.generator_class.capitalize()}",
            f"{PFX_INSTRUCTION_FREQUENCY}{FMT_INSTRUCTION_FREQUENCY.format(fragment.frequency)}",
            f"{PFX_INSTRUCTION_SAMPLE_LENGTH}{len(fragment.sample)}{SUF_INSTRUCTION_SAMPLE_LENGTH}",
            f"{PFX_INSTRUCTION_OFFSET}{fragment.offset}",
            "",
            LBL_INSTRUCTION_PARAMETERS_HEADER,
        ]

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(field_value)
            lines.append(f"{PFX_INSTRUCTION_PARAMETER_INDENT}{field_name}: {formatted_value}")

        return "\n".join(lines)

    def _format_parameter_value(self, value: Union[float, bool, list, tuple, str, int]) -> str:
        if isinstance(value, float):
            return f"{value:.{VAL_INSTRUCTION_FLOAT_PRECISION}f}"
        elif isinstance(value, bool):
            return LBL_GLOBAL_YES if value else LBL_GLOBAL_NO
        elif isinstance(value, (list, tuple)):
            return f"[{', '.join(str(v) for v in value)}]"
        else:
            return str(value)


class InstructionDetailsPanel:
    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.logic = InstructionDetailsLogic()
        self.info_tag = f"{tag}_instruction_info"

    def create_panel(self, parent: Optional[Union[int, str]] = None) -> None:
        if parent is not None:
            with dpg.group(tag=self.tag, parent=parent):
                dpg.add_text(MSG_INSTRUCTION_DETAILS)
                dpg.add_separator()
                dpg.add_text(MSG_INSTRUCTION_NO_SELECTION, tag=self.info_tag)
        else:
            with dpg.group(tag=self.tag):
                dpg.add_text(MSG_INSTRUCTION_DETAILS)
                dpg.add_separator()
                dpg.add_text(MSG_INSTRUCTION_NO_SELECTION, tag=self.info_tag)

    def display_instruction(
        self, generator_class_name: str, instruction: InstructionUnion, fragment: Optional[LibraryFragment] = None
    ) -> None:
        self.logic.set_instruction_data(generator_class_name, instruction, fragment)
        self._update_display()

    def clear_display(self) -> None:
        self.logic.clear_data()
        self._update_display()

    def _update_display(self) -> None:
        display_text = self.logic.get_display_text()
        dpg.set_value(self.info_tag, display_text)
