from pathlib import Path

from pydantic import BaseModel

from sampletones_core.constants.enums import SpectrumMethod


class AdvancedSettingsPanelViewModel(BaseModel, frozen=True):
    max_workers: int
    spectrum_method: SpectrumMethod
    transformation_gamma: int
    library_directory: Path
    reconstructions_directory: Path
