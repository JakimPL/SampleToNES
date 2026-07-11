from pydantic import BaseModel


class PlayerCardLayout(BaseModel, frozen=True):
    width: int


class PlayerButtonLayout(BaseModel, frozen=True):
    height: int
    width: int
    gap: int


class PlayerLayout(BaseModel, frozen=True):
    card: PlayerCardLayout
    button: PlayerButtonLayout
    toolbar: PlayerButtonLayout
