from pydantic import BaseModel


class CommonGlyphs(BaseModel, extra="forbid", frozen=True):
    tick: str
    favorite: str
    expanded: str
    collapsed: str
    chevron_left: str
    chevron_right: str
