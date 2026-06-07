from typing import Optional

from pydantic.dataclasses import dataclass

from sampletones_core.constants.enums import GeneratorName


@dataclass(frozen=True)
class EditAction:
    row: int
    generator: Optional[GeneratorName]
    sample_idex: Optional[int]
    transpose: Optional[int]
    volume: Optional[int]


@dataclass
class ClearAction:
    row: int
    generator: Optional[GeneratorName]
