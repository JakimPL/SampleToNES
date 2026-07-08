from pydantic import BaseModel


class CommonGlyphs(BaseModel, frozen=True):
    tick: str
    favorite: str


class HeaderGlyphs(BaseModel, frozen=True):
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
    project: str
    samples: str
    tracker: str
    order: str
    history: str


class PlayerGlyphs(BaseModel, frozen=True):
    play: str
    pause: str
    stop: str


class Glyphs(BaseModel, frozen=True):
    common: CommonGlyphs
    headers: HeaderGlyphs
    player: PlayerGlyphs


class GlyphLayout(BaseModel, frozen=True):
    indent: int
    width: int
