from pydantic import BaseModel


class SettingsWindowLayout(BaseModel, frozen=True):
    width: int
    height: int


class SettingsLayout(BaseModel, frozen=True):
    window: SettingsWindowLayout
    combo_width: int
    label_width: int
