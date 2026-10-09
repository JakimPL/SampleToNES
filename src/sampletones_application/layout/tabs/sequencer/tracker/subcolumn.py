from pydantic import BaseModel


class SubcolumnWidths(BaseModel, extra="forbid", frozen=True):
    voice: int
    transpose: int
    volume: int
