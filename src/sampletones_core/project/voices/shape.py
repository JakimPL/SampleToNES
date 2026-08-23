from functools import cached_property
from typing import Dict, List, Literal, Optional, Self, Tuple
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.constants.general import (
    MAX_PERIOD,
    MAX_PITCH,
    MIN_PITCH,
)
from sampletones_core.exporters.feature import Features
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.features import (
    CHANNEL_GENERATOR_KIND,
    RESTING_REFERENCE_PERIOD,
    RESTING_REFERENCE_PITCH,
    channel_reference,
    supported_features,
    supports,
)
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.voices.envelopes import ShapeEnvelopes


def _new_shape_id() -> str:
    return uuid4().hex


class Shape(BaseModel):
    """A hand-written voice: envelopes with no recording behind them, playable on any channel.

    Where a sample carries the frames a conversion found for each channel, a shape carries one set
    of envelopes and every channel reads what it can of them — the dimensions its generator offers,
    measured against the root the shape states. That is the FamiTracker instrument model, so a
    shape reaches a tracker as one instrument and sounds here as the frames each channel makes of
    it.

    A shape carries no payload beyond what it states, so a project stores it whole rather than
    beside itself: this is both the voice a song plays and the record a ``project.json`` holds.

    Attributes:
        id: Stable id the tracker rows reference.
        name: The name the voice list shows.
        envelopes: The per-tick values every channel reads.
        root_pitch: The note a tonal channel measures the arpeggio against.
        root_period: The period the noise channel measures the arpeggio against.
        loop_point: The tick the envelopes repeat from, or ``None`` where they play once.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["shape"] = "shape"
    id: str = Field(default_factory=_new_shape_id, description="Stable shape id.")
    name: str = Field(..., description="Shape name.")
    envelopes: ShapeEnvelopes = Field(default_factory=ShapeEnvelopes)
    root_pitch: int = Field(
        default=RESTING_REFERENCE_PITCH,
        ge=MIN_PITCH,
        le=MAX_PITCH,
        description="Note a tonal channel measures the arpeggio envelope against.",
    )
    root_period: int = Field(
        default=RESTING_REFERENCE_PERIOD,
        ge=0,
        le=MAX_PERIOD,
        description="Period the noise channel measures the arpeggio envelope against.",
    )
    loop_point: Optional[int] = Field(
        default=None,
        ge=0,
        description="Tick the envelopes repeat from, or None where they play once.",
    )

    @property
    def loops(self) -> bool:
        """Whether the shape repeats its envelopes rather than playing them once."""
        return self.loop_point is not None

    def reference(self, channel_name: ChannelName) -> int:
        """The value this channel measures the arpeggio envelope against."""
        return channel_reference(
            channel_name,
            pitch=self.root_pitch,
            period=self.root_period,
        )

    def held_features(self, channel_name: ChannelName) -> Tuple[FeatureKey, ...]:
        """The dimensions this channel governs: those it offers and the shape leaves empty."""
        kind = CHANNEL_GENERATOR_KIND[channel_name]
        return tuple(
            feature_key
            for feature_key in supported_features(kind)
            if not self.envelopes.envelope_map.get(feature_key, ())
        )

    def features(self, channel_name: ChannelName) -> Features:
        """The envelopes as this channel reads them, measured against the shape's root.

        A channel takes the dimensions its generator offers and leaves the rest absent, which is
        what makes one set of envelopes serve every channel.

        Args:
            channel_name: The channel reading the shape.

        Returns:
            Features: The per-dimension envelopes for that channel.
        """
        kind = CHANNEL_GENERATOR_KIND[channel_name]
        return Features(
            initial_pitch=self.reference(channel_name),
            volume=_items(self.envelopes.volume),
            arpeggio=_items(self.envelopes.arpeggio),
            pitch=None,
            hi_pitch=None,
            duty_cycle=(_items(self.envelopes.duty_cycle) if supports(kind, FeatureKey.DUTY_CYCLE) else None),
        )

    @cached_property
    def _instructions(self) -> Dict[ChannelName, List[InstructionUnion]]:
        return {
            channel_name: list(CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(self.features(channel_name)))
            for channel_name in ChannelName.items()
        }

    def instructions(self, channel_name: ChannelName) -> List[InstructionUnion]:
        """The frames this channel plays, one per tick of the envelopes.

        Args:
            channel_name: The channel sounding the shape.

        Returns:
            List[InstructionUnion]: The frames, empty where the shape writes no envelope.
        """
        return self._instructions[channel_name]

    def invalidate(self) -> None:
        """Drops the memoized frames so they are made afresh from the envelopes they describe."""
        self.__dict__.pop("_instructions", None)

    def clone(self) -> Self:
        """Return an independent copy with a fresh id, carrying the name, root and envelopes."""
        return type(self)(
            name=self.name,
            envelopes=self.envelopes,
            root_pitch=self.root_pitch,
            root_period=self.root_period,
            loop_point=self.loop_point,
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Shape) and self.id == other.id

    def __repr__(self) -> str:
        return f"Shape(id={self.id!r}, name={self.name!r})"


def _items(envelope: Tuple[int, ...]) -> np.ndarray:
    return np.array(envelope, dtype=np.int8)
