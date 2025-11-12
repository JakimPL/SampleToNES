from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field

from sampletones.instructions import InstructionUnion
from sampletones.library import LibraryFragment


class InstructionPanelData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_class_name: str
    instruction: InstructionUnion
    fragment: Optional[LibraryFragment] = None

    @computed_field
    @property
    def frequency(self) -> Optional[float]:
        return self.fragment.frequency if self.fragment else None

    @computed_field
    @property
    def has_audio_data(self) -> bool:
        return self.fragment is not None and len(self.fragment.sample) > 0
