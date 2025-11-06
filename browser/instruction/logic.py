from typing import Optional, Union

from browser.instruction.data import InstructionPanelData
from constants.browser import (
    FMT_INSTRUCTION_FREQUENCY,
    LBL_GLOBAL_NO,
    LBL_GLOBAL_YES,
    LBL_INSTRUCTION_PARAMETERS_HEADER,
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
            f"{PFX_INSTRUCTION_GENERATOR}{fragment.generator_class}",
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
