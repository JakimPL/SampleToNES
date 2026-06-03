from pydantic import BaseModel


class PlayerPanelLayout(BaseModel, frozen=True):
    width: int
    height: int


class ControlsTableLayout(BaseModel, frozen=True):
    height: int


class PlayerLayout(BaseModel, frozen=True):
    panel: PlayerPanelLayout
    controls_table: ControlsTableLayout
