from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryFragment, InstructionLibraryKey


class InstructionPanelData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    library_key: InstructionLibraryKey
    instruction: InstructionUnion
    config: InstructionsLibraryConfig
    fragment: InstructionLibraryFragment[Any]

    @property
    def frequency(self) -> Optional[float]:
        return self.fragment.frequency if self.fragment else None

    @property
    def generator_class_name(self) -> GeneratorClassName:
        return self.fragment.generator_class
