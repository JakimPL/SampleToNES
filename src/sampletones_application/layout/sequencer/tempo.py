from pydantic import BaseModel


class TempoLayout(BaseModel, extra="forbid", frozen=True):
    min: int
    max: int
    default: int
