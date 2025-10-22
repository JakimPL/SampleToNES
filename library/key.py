import hashlib
import json
from typing import Self

from pydantic import BaseModel, Field

from config import Config as Config
from constants import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from ffts.window import Window
from utils.common import dump


class LibraryKey(BaseModel):
    sample_rate: int = Field(..., ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE, description="Sample rate of the audio")
    frame_length: int = Field(..., ge=1, description="Length of a single frame")
    window_size: int = Field(..., ge=1, description="Size of the FFT window")
    config_hash: str = Field(..., description="Hash of the configuration")

    @classmethod
    def create(cls, config: Config, window: Window) -> Self:
        config_fields = {
            "change_rate": config.change_rate,
            "sample_rate": config.sample_rate,
            "a4_frequency": config.a4_frequency,
            "a4_pitch": config.a4_pitch,
        }
        json_string = dump(config_fields)
        config_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()
        return cls(
            sample_rate=config.sample_rate,
            frame_length=window.frame_length,
            window_size=window.size,
            config_hash=config_hash,
        )

    @classmethod
    def deserialize(cls, string: str) -> Self:
        dictionary = json.loads(string)
        return cls(**dictionary)

    class Config:
        frozen = True
