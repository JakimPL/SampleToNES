from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.order import PlaneOrder


class CompressedPlanes(BaseModel):
    """A song's planes as the driver reads them: one dictionary and eight token streams.

    Attributes:
        phrases: The dictionary every stream's tokens name.
        streams: The tokens each plane is written as, in the order the song block writes them.
        ticks: The ticks the song lasts, which is where each stream stops being read.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    phrases: PhraseTable
    streams: PlaneOrder
    ticks: int

    @model_validator(mode="after")
    def _validate_the_song_lasts(self) -> CompressedPlanes:
        if self.ticks < 1:
            raise ValueError(f"a song lasts at least one tick, and this one lasts {self.ticks}")

        return self

    @property
    def size(self) -> int:
        """The bytes the dictionary and the eight streams take together."""
        return self.phrases.size + sum(len(stream) for stream in self.streams)
