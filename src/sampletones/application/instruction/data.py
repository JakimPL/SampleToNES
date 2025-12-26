from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from sampletones.configs import InstructionsLibraryConfig
from sampletones.constants.enums import GeneratorClassName
from sampletones.instructions import InstructionUnion
from sampletones.library import InstructionLibraryFragment


class InstructionPanelData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    instruction: InstructionUnion
    config: InstructionsLibraryConfig
    fragment: InstructionLibraryFragment[Any]

    @property
    def frequency(self) -> Optional[float]:
        return self.fragment.frequency if self.fragment else None

    @property
    def has_audio_data(self) -> bool:
        return self.fragment is not None and not self.fragment.empty

    @property
    def generator_class_name(self) -> GeneratorClassName:
        return self.fragment.generator_class
