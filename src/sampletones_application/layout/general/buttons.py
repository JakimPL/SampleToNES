from pydantic import BaseModel


class ButtonsLayout(BaseModel, extra="forbid", frozen=True):
    copy_width: int
