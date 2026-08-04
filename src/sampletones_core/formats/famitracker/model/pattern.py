from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_core.formats.famitracker.specification.channels import ChannelId


class NoteCell(BaseModel):
    """A resolved note column: a note value (1-12, or a reserved marker) and octave."""

    model_config = ConfigDict(frozen=True)

    note: int
    octave: int


class RowCell(BaseModel):
    """One populated pattern row on a single channel.

    Carries the FamiTracker cell columns: note, octave, instrument index, volume and
    the per-column effects. ``row_number`` is the row's position within the pattern.
    """

    model_config = ConfigDict(frozen=True)

    row_number: int
    note: int
    octave: int
    instrument: int
    volume: int
    effects: Tuple[Tuple[int, int], ...]


class PatternData(BaseModel):
    """A pattern's populated rows on one channel, addressed by its pool index."""

    model_config = ConfigDict(frozen=True)

    channel: ChannelId
    index: int
    rows: Tuple[RowCell, ...]
