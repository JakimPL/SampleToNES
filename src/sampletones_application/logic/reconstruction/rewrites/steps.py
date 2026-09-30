from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, TypeAlias, Union

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope
from sampletones_shared.types.callback import VoidCallback


@dataclass(frozen=True)
class ChannelChange:
    """What a reader moved on one channel of the instruments panel.

    A change carries the dimensions the reader moved alone, and at its turn it is written over the
    envelopes the document then holds. The rest of the channel is read at that turn, so what a step
    before it rebuilt stands, and a frame a removal released keeps resting.

    Attributes:
        channel_name: The channel the reader moved.
        feature_key: The dimension moved last, which the history names the edit by.
        envelopes: Each dimension moved, as the reader left it.
        initial_pitch: The pitch the arpeggio is measured against, where the reader moved it.
    """

    channel_name: ChannelName
    feature_key: FeatureKey
    envelopes: Mapping[FeatureKey, Envelope[int]]
    initial_pitch: Optional[int]

    def merged(self, later: ChannelChange) -> ChannelChange:
        """This change followed by ``later``, as one change carrying what both moved.

        A dimension both moved takes the later value, and so does the pitch where the later change
        moved it, so a drag collapses into the place it ended.

        Raises:
            ValueError: If ``later`` moves another channel.
        """
        if later.channel_name != self.channel_name:
            raise ValueError(f"A change of {later.channel_name} merges into a change of that channel alone")

        return ChannelChange(
            channel_name=self.channel_name,
            feature_key=later.feature_key,
            envelopes={**self.envelopes, **later.envelopes},
            initial_pitch=self.initial_pitch if later.initial_pitch is None else later.initial_pitch,
        )

    def rebased(self, features: Features) -> Features:
        """The channel's envelopes as ``features`` holds them, with what this change moved written over them."""
        rebased = (
            features
            if self.initial_pitch is None
            else features.model_copy(update={"initial_pitch": self.initial_pitch})
        )
        for feature_key, envelope in self.envelopes.items():
            rebased = rebased.with_envelope(feature_key, envelope)

        return rebased


@dataclass(frozen=True)
class StemRemovalRequest:
    """A reader taking a recording out of the document, named as the history reports it."""

    stem_id: int
    stem_name: str


@dataclass(frozen=True)
class RateChange:
    """The document re-timed to another NES frequency."""

    nes_frequency: int


@dataclass(frozen=True)
class AfterEdits:
    """A gesture that reads or puts away the whole document, run once the edits before it have landed."""

    gesture: VoidCallback


Rewrite: TypeAlias = Union[ChannelChange, StemRemovalRequest, RateChange, AfterEdits]
