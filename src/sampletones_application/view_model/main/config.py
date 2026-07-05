from pydantic import BaseModel

from sampletones_core.constants.enums import SpectrumMethod


class ConfigPanelViewModel(BaseModel, frozen=True):
    normalize: bool
    quantize: bool
    sample_rate: int
    nes_frequency: int
    spectrum_method: SpectrumMethod
    transformation_gamma: int
