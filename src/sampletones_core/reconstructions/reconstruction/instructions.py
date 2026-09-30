from __future__ import annotations

from typing import Iterable, List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.data import DataModel
from sampletones_core.features import resting_held_features, resting_reference
from sampletones_core.instructions import InstructionData, InstructionUnion, sounds


class InstructionsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    channel_name: ChannelName = Field(
        ...,
        description="Name of the channel",
    )
    instructions: List[InstructionData[InstructionUnion]] = Field(
        ...,
        description="List of instruction data for the channel",
    )
    initial_pitch: int = Field(
        ...,
        description="Reference pitch the channel's arpeggio envelope is measured against",
    )
    held_features: List[FeatureKey] = Field(
        ...,
        description="Dimensions the channel governs, sounding at the value every note starts on",
    )

    @model_validator(mode="after")
    def _validate_a_stream_sounds(self) -> Self:
        """Holds a stored stream to sounding somewhere, since a channel resting throughout stands by.

        Raises:
            ValueError: If the stream holds frames and none of them sounds.
        """
        if self.instructions and not self.sounds:
            raise ValueError(f"The {self.channel_name} stream rests through every frame it holds")

        return self

    @property
    def sounds(self) -> bool:
        """Whether the channel sounds in some frame, which is what puts it in play."""
        return sounds(data.instruction for data in self.instructions)

    @classmethod
    def create(
        cls,
        channel_name: ChannelName,
        instructions: List[InstructionUnion],
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
    ) -> InstructionsItem:
        """The stream a channel plays, stored as no frame at all where it sounds in none.

        A channel resting through every frame stands by, whatever left it silent, so its stream
        describes no frame. The reference and the held dimensions stay those handed in, so a
        channel an edit or a removal silences keeps the base it was shaped from.

        Args:
            channel_name: The channel the stream belongs to.
            instructions: What the channel plays, one instruction per frame.
            initial_pitch: The reference the channel's arpeggio envelope is measured against.
            held_features: The dimensions the channel governs.

        Returns:
            InstructionsItem: The stream the channel carries.
        """
        stored = instructions if sounds(instructions) else []
        return InstructionsItem(
            channel_name=channel_name,
            instructions=[
                InstructionData(
                    instruction_class=instruction.class_name(),
                    instruction=instruction,
                )
                for instruction in stored
            ],
            initial_pitch=initial_pitch,
            held_features=list(held_features),
        )

    @classmethod
    def resting(cls, channel_name: ChannelName) -> InstructionsItem:
        """The stream a channel carries while it stands by, describing no frame.

        A reconstruction holds one stream per channel, so a channel it leaves silent is
        present and editable: it rests at the reference its first envelope will sound at,
        and describing a frame is what puts it back in play. Writing no frame leaves every
        dimension the channel offers to the channel, which is what an edit clearing the last
        frame records and what an export of this stream reads back.

        Args:
            channel_name: The channel the resting stream belongs to.

        Returns:
            InstructionsItem: The stream of a channel that stands by.
        """
        return cls(
            channel_name=channel_name,
            instructions=[],
            initial_pitch=resting_reference(channel_name),
            held_features=list(resting_held_features(channel_name)),
        )
