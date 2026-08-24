from typing import Annotated, Dict

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import (
    ARPEGGIO_MAX,
    ARPEGGIO_MIN,
    MAX_DUTY_CYCLE,
    MAX_VOLUME,
    SILENT_VOLUME,
)
from sampletones_core.features.envelope import Envelope

VolumeItem = Annotated[int, Field(ge=SILENT_VOLUME, le=MAX_VOLUME)]
ArpeggioItem = Annotated[int, Field(ge=ARPEGGIO_MIN, le=ARPEGGIO_MAX)]
DutyCycleItem = Annotated[int, Field(ge=0, le=MAX_DUTY_CYCLE)]


class InstrumentEnvelopes(BaseModel):
    """The per-tick envelopes an instrument writes, in the terms every channel reads them in.

    Each dimension carries the widest range the four channels offer, and a channel takes what it
    reads: an arpeggio item is a semitone offset on the tonal channels and a period offset on
    noise, and a duty-cycle item selects a pulse waveform or the noise channel's short mode. An
    empty envelope leaves that dimension to the channel, which keeps the value it already holds —
    the same record a reconstruction's held dimensions carry.

    Attributes:
        volume: Output level per tick.
        arpeggio: Offset from the instrument's initial pitch per tick.
        duty_cycle: Pulse waveform, or noise mode, per tick.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    volume: Envelope[VolumeItem] = Envelope[VolumeItem]()
    arpeggio: Envelope[ArpeggioItem] = Envelope[ArpeggioItem]()
    duty_cycle: Envelope[DutyCycleItem] = Envelope[DutyCycleItem]()

    @property
    def envelope_map(self) -> Dict[FeatureKey, Envelope[int]]:
        return {
            FeatureKey.VOLUME: self.volume,
            FeatureKey.ARPEGGIO: self.arpeggio,
            FeatureKey.DUTY_CYCLE: self.duty_cycle,
        }

    def envelope(self, feature_key: FeatureKey) -> Envelope[int]:
        """The dimension one feature names, empty where the instrument leaves it to the channel.

        Args:
            feature_key: The dimension read.

        Returns:
            Envelope[int]: That dimension's items and loop point.

        Raises:
            KeyError: If ``feature_key`` names a dimension an instrument does not write.
        """
        return self.envelope_map[feature_key]

    def with_envelope(self, feature_key: FeatureKey, envelope: Envelope[int]) -> "InstrumentEnvelopes":
        """The envelopes with one dimension replaced.

        Args:
            feature_key: The dimension written.
            envelope: What that dimension now carries; empty items leave it to the channel.

        Returns:
            InstrumentEnvelopes: The envelopes carrying ``envelope`` for ``feature_key``.

        Raises:
            KeyError: If ``feature_key`` names a dimension an instrument does not write.
        """
        if feature_key not in self.envelope_map:
            raise KeyError(feature_key)

        return self.model_copy(update={feature_key.value: envelope})

    @property
    def frame_count(self) -> int:
        """The ticks the envelopes describe, taken from the longest dimension."""
        return max((len(envelope.items) for envelope in self.envelope_map.values()), default=0)
