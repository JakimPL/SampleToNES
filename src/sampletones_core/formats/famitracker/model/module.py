from __future__ import annotations

from typing import Dict, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.pattern import PatternData
from sampletones_core.formats.famitracker.specification.channels import ChannelId
from sampletones_core.formats.famitracker.specification.parameters import Machine

OrderFrame = Tuple[int, ...]
"""One order position: the pattern index each channel plays, in channel-id order."""


class ModuleParameters(BaseModel):
    """The PARAMS block values: chip, channel count, machine and playback settings."""

    model_config = ConfigDict(frozen=True)

    expansion_chip: int
    channel_count: int
    machine: Machine
    engine_speed: int
    vibrato_style: int
    highlight_first: int
    highlight_second: int
    speed_split_point: int


class ModuleInformation(BaseModel):
    """The INFO block values: title, author and copyright."""

    model_config = ConfigDict(frozen=True)

    title: str
    author: str
    copyright: str


class Track(BaseModel):
    """One FamiTracker track: its timing, order table, patterns and effect columns."""

    model_config = ConfigDict(frozen=True)

    title: str
    speed: int
    tempo: int
    rows_per_pattern: int
    order: Tuple[OrderFrame, ...]
    patterns: Tuple[PatternData, ...]
    effect_columns: Dict[ChannelId, int]


class FamiTrackerModule(BaseModel):
    """A complete FamiTracker module ready for serialization to ``.ftm``."""

    model_config = ConfigDict(frozen=True)

    parameters: ModuleParameters
    information: ModuleInformation
    instruments: Tuple[Instrument2A03, ...]
    track: Track
    comment: str
