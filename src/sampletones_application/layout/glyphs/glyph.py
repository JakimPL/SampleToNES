from pydantic import BaseModel


class GlyphLayout(BaseModel, extra="forbid", frozen=True):
    indent: int
    width: int
    top_offset: int
