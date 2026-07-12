from pydantic import BaseModel


class PlayerToolbarLayout(BaseModel, extra="forbid", frozen=True):
    indent: int
    width: int
    height: int
    padding: int
    gap: int


class PlayerButtonLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    width: int


class PlayerLayout(BaseModel, extra="forbid", frozen=True):
    toolbar: PlayerToolbarLayout
    button: PlayerButtonLayout
