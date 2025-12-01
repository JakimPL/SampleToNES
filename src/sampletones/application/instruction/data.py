from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from sampletones.instructions import InstructionUnion
from sampletones.library import InstructionLibraryFragment


class InstructionPanelData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_class_name: str
    instruction: InstructionUnion
    fragment: Optional[InstructionLibraryFragment[Any]] = None

    @property
    def frequency(self) -> Optional[float]:
        return self.fragment.frequency if self.fragment else None

    @property
    def has_audio_data(self) -> bool:
        return self.fragment is not None and not self.fragment.empty
