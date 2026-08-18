from pydantic import BaseModel


class SubcolumnWidths(BaseModel, extra="forbid", frozen=True):
    instrument: int
    transpose: int
    volume: int
