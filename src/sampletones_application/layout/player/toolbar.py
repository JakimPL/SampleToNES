from pydantic import BaseModel


class PlayerToolbarLayout(BaseModel, extra="forbid", frozen=True):
    indent: int
    width: int
    height: int
    padding: int
    gap: int
