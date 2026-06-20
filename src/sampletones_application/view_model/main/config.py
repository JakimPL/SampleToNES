from pydantic import BaseModel


class ConfigPanelViewModel(BaseModel, frozen=True):
    normalize: bool
    quantize: bool
    sample_rate: int
    nes_frequency: int
    transformation_gamma: int
