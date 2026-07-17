from pydantic import BaseModel


class HistoryLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    selectable_column_weight: float
    max_rendered_entries: int
