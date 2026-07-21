from pydantic import BaseModel


class AdvancedLayout(BaseModel, extra="forbid", frozen=True):
    height: int
    button_height: int
