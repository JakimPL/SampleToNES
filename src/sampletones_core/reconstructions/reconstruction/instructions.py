from __future__ import annotations

from typing import Iterable, List

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.data import DataModel
from sampletones_core.features import resting_held_features, resting_reference
from sampletones_core.instructions import InstructionData, InstructionUnion


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
        description="Dimensions the channel governs, keeping the value it holds while the channel sounds",
    )

    @classmethod
    def create(
        cls,
        channel_name: ChannelName,
        instructions: List[InstructionUnion],
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
    ) -> InstructionsItem:
        return InstructionsItem(
            channel_name=channel_name,
            instructions=[
                InstructionData(
                    instruction_class=instruction.class_name(),
                    instruction=instruction,
                )
                for instruction in instructions
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
        return cls.create(
            channel_name=channel_name,
            instructions=[],
            initial_pitch=resting_reference(channel_name),
            held_features=resting_held_features(channel_name),
        )
