from typing import Annotated, Dict, Tuple

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import (
    ARPEGGIO_MAX,
    ARPEGGIO_MIN,
    MAX_DUTY_CYCLE,
    MAX_VOLUME,
    SILENT_VOLUME,
)

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
        arpeggio: Offset from the instrument's root per tick.
        duty_cycle: Pulse waveform, or noise mode, per tick.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    volume: Tuple[VolumeItem, ...] = ()
    arpeggio: Tuple[ArpeggioItem, ...] = ()
    duty_cycle: Tuple[DutyCycleItem, ...] = ()

    @property
    def envelope_map(self) -> Dict[FeatureKey, Tuple[int, ...]]:
        return {
            FeatureKey.VOLUME: self.volume,
            FeatureKey.ARPEGGIO: self.arpeggio,
            FeatureKey.DUTY_CYCLE: self.duty_cycle,
        }

    def envelope(self, feature_key: FeatureKey) -> Tuple[int, ...]:
        """The items one dimension carries, empty where the instrument leaves it to the channel.

        Args:
            feature_key: The dimension read.

        Returns:
            Tuple[int, ...]: That dimension's items.

        Raises:
            KeyError: If ``feature_key`` names a dimension an instrument does not write.
        """
        return self.envelope_map[feature_key]

    def with_envelope(self, feature_key: FeatureKey, items: Tuple[int, ...]) -> "InstrumentEnvelopes":
        """The envelopes with one dimension replaced.

        Args:
            feature_key: The dimension written.
            items: What that dimension now carries; empty leaves it to the channel.

        Returns:
            InstrumentEnvelopes: The envelopes carrying ``items`` for ``feature_key``.

        Raises:
            KeyError: If ``feature_key`` names a dimension an instrument does not write.
        """
        if feature_key not in self.envelope_map:
            raise KeyError(feature_key)

        return self.model_copy(update={feature_key.value: items})

    @property
    def frame_count(self) -> int:
        """The ticks the envelopes describe, taken from the longest dimension."""
        return max((len(items) for items in self.envelope_map.values()), default=0)
