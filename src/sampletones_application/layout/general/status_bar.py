from pydantic import BaseModel


class StatusBarLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    reserved_margin: int
