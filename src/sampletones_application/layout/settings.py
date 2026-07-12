from pydantic import BaseModel


class SettingsWindowLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    height: int


class SettingsLayout(BaseModel, extra="forbid", frozen=True):
    window: SettingsWindowLayout
    combo_width: int
    label_width: int
