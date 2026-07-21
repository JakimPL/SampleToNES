from pydantic import BaseModel


class SpeedLayout(BaseModel, extra="forbid", frozen=True):
    min: int
    max: int
    default: int
