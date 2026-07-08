from pydantic import BaseModel


class GlyphsLayout(BaseModel, frozen=True):
    tick: str
    favorite: str
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
