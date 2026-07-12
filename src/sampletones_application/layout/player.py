from pydantic import BaseModel


class PlayerToolbarLayout(BaseModel, extra="forbid", frozen=True):
    width: int
    padding: int


class PlayerButtonLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    width: int
    gap: int


class PlayerLayout(BaseModel, extra="forbid", frozen=True):
    toolbar: PlayerToolbarLayout
    button: PlayerButtonLayout
