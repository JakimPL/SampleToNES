from pydantic import BaseModel


class DialogSizeNoWidth(BaseModel, extra="forbid", frozen=True):
    height: int
