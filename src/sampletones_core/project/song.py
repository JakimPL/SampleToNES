from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field

from sampletones_core.constants.enums import GeneratorName

from .patterns.channel import Channel


class Song(BaseModel):
    """The pattern arrangement across the four NES channels.

    Each :class:`GeneratorName` maps to an independent :class:`Channel`. Channels
    do not share patterns; the song is simply their parallel composition.
    """

    channels: Dict[GeneratorName, Channel] = Field(..., description="One independent track per NES channel.")

    @classmethod
    def empty(cls, rows_per_pattern: int) -> Song:
        channels = {generator: Channel.empty(generator, rows_per_pattern) for generator in GeneratorName.items()}
        return cls(channels=channels)

    def __getitem__(self, generator: GeneratorName) -> Channel:
        return self.channels[generator]

    def __repr__(self) -> str:
        return f"Song(channels={list(self.channels)})"
