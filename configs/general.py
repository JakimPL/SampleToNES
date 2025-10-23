from pydantic import BaseModel, Field

from constants import LIBRARY_DIRECTORY, MAX_PITCH, MAX_WORKERS, MIN_PITCH, MIXER


class GeneralConfig(BaseModel):
    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    mixer: float = Field(default=MIXER, ge=0.0, le=100.0)
    library_directory: str = Field(default=LIBRARY_DIRECTORY)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    class Config:
        frozen = True
