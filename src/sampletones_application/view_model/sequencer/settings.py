from pydantic import BaseModel


class SequencerSettingsViewModel(BaseModel, frozen=True):
    nes_frequency: int
    tempo: int
    speed: int
    rows_per_pattern: int
