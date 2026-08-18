from pydantic import BaseModel


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
