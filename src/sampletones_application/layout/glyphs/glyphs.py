from pydantic import BaseModel

from sampletones_application.layout.glyphs.common import CommonGlyphs
from sampletones_application.layout.glyphs.header import HeaderGlyphs
from sampletones_application.layout.glyphs.player import PlayerGlyphs


class Glyphs(BaseModel, extra="forbid", frozen=True):
    common: CommonGlyphs
    headers: HeaderGlyphs
    player: PlayerGlyphs
