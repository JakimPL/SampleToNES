from pydantic import BaseModel


class PlayerGlyphs(BaseModel, extra="forbid", frozen=True):
    play: str
    pause: str
    resume: str
    stop: str
