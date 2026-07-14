from pydantic import BaseModel


class MenuLayout(BaseModel, extra="forbid", frozen=True):
    fps_text_offset: int
