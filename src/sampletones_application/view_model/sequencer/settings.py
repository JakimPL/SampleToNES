from pydantic import BaseModel


class SequencerSettingsViewModel(BaseModel, frozen=True):
    change_rate: int
    tempo: int
    speed: int
    rows_per_pattern: int
