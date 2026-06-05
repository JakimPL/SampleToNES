from pydantic import BaseModel


class ConfigPanelViewModel(BaseModel, frozen=True):
    normalize: bool
    quantize: bool
    sample_rate: int
    change_rate: int
    transformation_gamma: int
