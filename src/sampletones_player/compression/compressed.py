from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.planes.order import PlaneOrder


class CompressedPlanes(BaseModel):
    """A song's planes as the driver reads them: one dictionary and a token stream per plane.

    Attributes:
        phrases: The dictionary every stream's tokens name.
        streams: The tokens each plane is written as, in the order the song block writes them.
        ticks: The ticks the song lasts, which is where each stream stops being read.
        loop_entries: The byte each stream is re-entered at when the song comes round, counted
            from that stream's own start, ``None`` for a plane holding no stream.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    phrases: PhraseTable
    streams: PlaneOrder
    ticks: int
    loop_entries: Tuple[Optional[int], ...]

    @model_validator(mode="after")
    def _validate_the_song_lasts(self) -> CompressedPlanes:
        if self.ticks < 1:
            raise ValueError(f"a song lasts at least one tick, and this one lasts {self.ticks}")

        return self

    @model_validator(mode="after")
    def _validate_every_stream_states_where_it_is_re_entered(self) -> CompressedPlanes:
        if len(self.loop_entries) != len(self.streams):
            raise ValueError(
                f"an entry stands for each of the {len(self.streams)} streams, " f"and {len(self.loop_entries)} stand"
            )

        return self

    @property
    def size(self) -> int:
        """The bytes the dictionary and every plane's stream take together."""
        return self.phrases.size + sum(len(stream) for stream in self.streams)
