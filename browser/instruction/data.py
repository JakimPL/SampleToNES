from typing import Optional

from pydantic import BaseModel, computed_field

from library.data import LibraryFragment
from typehints.instructions import InstructionUnion


class InstructionPanelData(BaseModel):
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

    class Config:
        arbitrary_types_allowed = True
        frozen = True
