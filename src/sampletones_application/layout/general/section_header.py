from pydantic import BaseModel

from sampletones_application.layout.glyphs.glyph import GlyphLayout


class SectionHeaderLayout(BaseModel, extra="forbid", frozen=True):
    glyph: GlyphLayout
    chevron_offset: int
