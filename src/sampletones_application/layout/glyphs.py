from pydantic import BaseModel


class CommonGlyphs(BaseModel, extra="forbid", frozen=True):
    tick: str
    favorite: str
    expanded: str
    collapsed: str


class HeaderGlyphs(BaseModel, extra="forbid", frozen=True):
    waveform: str
    spectrum: str
    reconstruction: str
    converter: str
    settings: str
    advanced: str
    filesystem: str
    instruction_data: str
    details: str
    parameters: str
    source: str
    instruments: str
    samples: str
    tracker: str
    order: str
    history: str


class PlayerGlyphs(BaseModel, extra="forbid", frozen=True):
    play: str
    pause: str
    resume: str
    stop: str


class Glyphs(BaseModel, extra="forbid", frozen=True):
    common: CommonGlyphs
    headers: HeaderGlyphs
    player: PlayerGlyphs


class GlyphLayout(BaseModel, extra="forbid", frozen=True):
    indent: int
    width: int
