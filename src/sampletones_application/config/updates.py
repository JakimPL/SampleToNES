from pathlib import Path
from typing import List

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class AudioSettingsUpdate(BaseModel, frozen=True):
    normalize: bool
    quantize: bool


class LibrarySettingsUpdate(BaseModel, frozen=True):
    sample_rate: int
    change_rate: int
    transformation_gamma: int


class GenerationSettingsUpdate(BaseModel, frozen=True):
    mixer: float
    generators: List[GeneratorName]


class AdvancedSettingsUpdate(BaseModel, frozen=True):
    max_workers: int
    library_directory: Path
    output_directory: Path
