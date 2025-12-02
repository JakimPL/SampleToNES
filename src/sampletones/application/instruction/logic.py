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
    LBL_INSTRUCTION_PARAMETER_INDENT,
    LBL_INSTRUCTION_PARAMETERS_HEADER,
    LBL_INSTRUCTION_SAMPLE_LENGTH,
    MSG_INSTRUCTION_NO_FREQUENCY,
    MSG_INSTRUCTION_NO_SELECTION,
    SUF_INSTRUCTION_SAMPLE_LENGTH,
    VAL_INSTRUCTION_FLOAT_PRECISION,
)
from .data import InstructionPanelData


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

    def get_display_text(self) -> str:
        if not self.current_data:
            return MSG_INSTRUCTION_NO_SELECTION

        if not self.current_data.fragment:
            lines = [
                f"{LBL_INSTRUCTION_GENERATOR}{self.current_data.generator_class_name}",
                f"{LBL_INSTRUCTION_NAME}{self.current_data.instruction.name}",
                f"{LBL_INSTRUCTION_FREQUENCY}{MSG_INSTRUCTION_NO_FREQUENCY}",
            ]
            return "\n".join(lines)

        fragment = self.current_data.fragment
        instruction = self.current_data.instruction

        lines = [
            f"{LBL_INSTRUCTION_GENERATOR}{fragment.generator_class}",
            f"{LBL_INSTRUCTION_FREQUENCY}{FMT_INSTRUCTION_FREQUENCY.format(fragment.frequency)}",
            f"{LBL_INSTRUCTION_SAMPLE_LENGTH}{fragment.length}{SUF_INSTRUCTION_SAMPLE_LENGTH}",
            "",
            LBL_INSTRUCTION_PARAMETERS_HEADER,
        ]

        for field_name, field_value in instruction.model_dump().items():
            formatted_value = self._format_parameter_value(field_value)
            lines.append(f"{LBL_INSTRUCTION_PARAMETER_INDENT}{field_name}: {formatted_value}")

        return "\n".join(lines)

    def _format_parameter_value(self, value: Union[float, bool, List[Any], Tuple[Any, ...], str, int]) -> str:
        if isinstance(value, float):
            return f"{value:.{VAL_INSTRUCTION_FLOAT_PRECISION}f}"

        if isinstance(value, bool):
            return LBL_GLOBAL_YES if value else LBL_GLOBAL_NO

        if isinstance(value, (list, tuple)):
            return f"[{', '.join(str(v) for v in value)}]"

        return str(value)
