from functools import cached_property
from typing import Dict, List, Literal, Self, Tuple
from uuid import uuid4

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
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes


def _new_instrument_id() -> str:
    return uuid4().hex


class Instrument(BaseModel):
    """A hand-written voice: envelopes with no recording behind them, playable on any channel.

    Where a sample carries the frames a conversion found for each channel, an instrument carries
    one set of envelopes, and every channel reads what it can of them — the dimensions its
    generator offers, measured against the root the instrument states. That is the model
    FamiTracker itself holds, so one reaches a tracker as it stands and sounds here as the frames
    each channel makes of it.

    An instrument carries no payload beyond what it states, so a project stores it whole rather than
    beside itself: this is both the voice a song plays and the record a ``project.json`` holds.

    Attributes:
        id: Stable id the tracker rows reference.
        name: The name the voice list shows.
        envelopes: The per-tick values every channel reads, each with its own loop point.
        initial_pitch: The note a tonal channel measures the arpeggio against.
        initial_period: The period the noise channel measures the arpeggio against.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["instrument"] = "instrument"
    id: str = Field(default_factory=_new_instrument_id, description="Stable instrument id.")
    name: str = Field(..., description="Instrument name.")
    envelopes: InstrumentEnvelopes = Field(default_factory=InstrumentEnvelopes)
    initial_pitch: int = Field(
        default=RESTING_REFERENCE_PITCH,
        ge=MIN_PITCH,
        le=MAX_PITCH,
        description="Note a tonal channel measures the arpeggio envelope against.",
    )
    initial_period: int = Field(
        default=RESTING_REFERENCE_PERIOD,
        ge=0,
        le=MAX_PERIOD,
        description="Period the noise channel measures the arpeggio envelope against.",
    )

    def reference(self, channel_name: ChannelName) -> int:
        """The value this channel measures the arpeggio envelope against."""
        return channel_reference(
            channel_name,
            pitch=self.initial_pitch,
            period=self.initial_period,
        )

    def held_features(self, channel_name: ChannelName) -> Tuple[FeatureKey, ...]:
        """The dimensions this channel governs: those it offers and the instrument leaves empty."""
        kind = CHANNEL_GENERATOR_KIND[channel_name]
        return tuple(
            feature_key for feature_key in supported_features(kind) if not self.envelopes.envelope(feature_key).written
        )

    def features(self, channel_name: ChannelName) -> Features:
        """The envelopes as this channel reads them, measured against the instrument's pitch.

        A channel takes the dimensions its generator offers and leaves the rest absent, which is
        what makes one set of envelopes serve every channel. Each dimension travels with the item
        it repeats from, so a channel reads a loop the way the instrument wrote it.

        Args:
            channel_name: The channel reading the instrument.

        Returns:
            Features: The per-dimension envelopes for that channel.
        """
        return Features.of(self.reference(channel_name), self._offered(channel_name))

    def instrument_features(self) -> Features:
        """The envelopes as a tracker instrument holds them: every dimension the instrument writes.

        A tracker instrument is one set of sequences whatever channel plays it, and each channel
        reads what it can of them, so this is the whole of what a tracker export writes.

        Returns:
            Features: The envelopes, measured against the instrument's tonal pitch.
        """
        return Features.of(self.initial_pitch, self.envelopes.envelope_map)

    def instruction_at(self, channel_name: ChannelName, tick: int) -> InstructionUnion:
        """The frame this channel sounds at any tick of a held note.

        Every dimension is defined at every tick — it circles from its loop point or holds its
        last item — so a note goes on sounding for as long as a row asks for it, and a volume
        envelope ending at silence is what releases it.

        Args:
            channel_name: The channel sounding the instrument.
            tick: Ticks since the note started.

        Returns:
            InstructionUnion: The frame standing at that tick.
        """
        standing = {
            feature_key: Envelope[int](items=(item,)) if (item := envelope.at(tick)) is not None else Envelope[int]()
            for feature_key, envelope in self._offered(channel_name).items()
        }
        features = Features.of(self.reference(channel_name), standing)
        return CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(features)[0]

    def _offered(self, channel_name: ChannelName) -> Dict[FeatureKey, Envelope[int]]:
        """The dimensions this channel's generator reads, as the instrument writes them."""
        kind = CHANNEL_GENERATOR_KIND[channel_name]
        return {
            feature_key: envelope
            for feature_key, envelope in self.envelopes.envelope_map.items()
            if supports(kind, feature_key)
        }

    @cached_property
    def _instructions(self) -> Dict[ChannelName, List[InstructionUnion]]:
        return {
            channel_name: list(CHANNEL_TO_EXPORTER_MAP[channel_name].from_features(self.features(channel_name)))
            for channel_name in ChannelName.items()
        }

    def instructions(self, channel_name: ChannelName) -> List[InstructionUnion]:
        """The frames this channel plays, one per tick of the envelopes.

        Args:
            channel_name: The channel sounding the instrument.

        Returns:
            List[InstructionUnion]: The frames, empty where the instrument writes no envelope.
        """
        return self._instructions[channel_name]

    def invalidate(self) -> None:
        """Drops the memoized frames so they are made afresh from the envelopes they describe.

        The frames are read from the envelopes once and kept, so whoever writes ``envelopes``
        calls this in the same breath. That pairing is what keeps what an instrument plays and
        what it states the same thing.
        """
        self.__dict__.pop("_instructions", None)

    def clone(self) -> Self:
        """Return an independent copy with a fresh id, carrying the name, pitch and envelopes."""
        return type(self)(
            name=self.name,
            envelopes=self.envelopes,
            initial_pitch=self.initial_pitch,
            initial_period=self.initial_period,
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Instrument) and self.id == other.id

    def __repr__(self) -> str:
        return f"Instrument(id={self.id!r}, name={self.name!r})"
