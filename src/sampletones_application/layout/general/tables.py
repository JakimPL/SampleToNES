from pydantic import BaseModel


class TablesLayout(BaseModel, extra="forbid", frozen=True):
    label_width: int
