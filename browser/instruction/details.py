from typing import Optional, Union

import dearpygui.dearpygui as dpg

from browser.constants import (
    BOOL_NO_TEXT,
    BOOL_YES_TEXT,
    INSTRUCTION_FLOAT_PRECISION,
    INSTRUCTION_FREQUENCY_FORMAT,
    INSTRUCTION_FREQUENCY_PREFIX,
    INSTRUCTION_GENERATOR_PREFIX,
    INSTRUCTION_NAME_PREFIX,
    INSTRUCTION_NO_FREQUENCY,
    INSTRUCTION_OFFSET_PREFIX,
    INSTRUCTION_PARAMETER_INDENT,
    INSTRUCTION_PARAMETERS_HEADER,
    INSTRUCTION_SAMPLE_LENGTH_PREFIX,
    INSTRUCTION_SAMPLE_LENGTH_SUFFIX,
    MSG_INSTRUCTION_DETAILS,
    MSG_NO_INSTRUCTION_SELECTED,
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
            return MSG_NO_INSTRUCTION_SELECTED

        if not self.current_data.fragment:
            lines = [
                f"{INSTRUCTION_GENERATOR_PREFIX}{self.current_data.generator_class_name}",
                f"{INSTRUCTION_NAME_PREFIX}{self.current_data.instruction.name}",
                f"{INSTRUCTION_FREQUENCY_PREFIX}{INSTRUCTION_NO_FREQUENCY}",
            ]
            return "\n".join(lines)

        fragment = self.current_data.fragment
        instruction = self.current_data.instruction

        lines = [
            f"{INSTRUCTION_GENERATOR_PREFIX}{fragment.generator_class.capitalize()}",
            f"{INSTRUCTION_FREQUENCY_PREFIX}{INSTRUCTION_FREQUENCY_FORMAT.format(fragment.frequency)}",
            f"{INSTRUCTION_SAMPLE_LENGTH_PREFIX}{len(fragment.sample)}{INSTRUCTION_SAMPLE_LENGTH_SUFFIX}",
            f"{INSTRUCTION_OFFSET_PREFIX}{fragment.offset}",
            "",
            INSTRUCTION_PARAMETERS_HEADER,
        ]

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(field_value)
            lines.append(f"{INSTRUCTION_PARAMETER_INDENT}{field_name}: {formatted_value}")

        return "\n".join(lines)

    def _format_parameter_value(self, value: Union[float, bool, list, tuple, str, int]) -> str:
        if isinstance(value, float):
            return f"{value:.{INSTRUCTION_FLOAT_PRECISION}f}"
        elif isinstance(value, bool):
            return BOOL_YES_TEXT if value else BOOL_NO_TEXT
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
                dpg.add_text(MSG_NO_INSTRUCTION_SELECTED, tag=self.info_tag)
        else:
            with dpg.group(tag=self.tag):
                dpg.add_text(MSG_INSTRUCTION_DETAILS)
                dpg.add_separator()
                dpg.add_text(MSG_NO_INSTRUCTION_SELECTED, tag=self.info_tag)

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
