from pydantic import BaseModel


class VoiceGlyphs(BaseModel, extra="forbid", frozen=True):
    sample: str
    shape: str
