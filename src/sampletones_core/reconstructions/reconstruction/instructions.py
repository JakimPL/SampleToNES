from __future__ import annotations

from typing import Iterable, List

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.data import DataModel
from sampletones_core.instructions import InstructionData, InstructionUnion


class InstructionsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(
        ...,
        description="Name of the generator",
    )
    instructions: List[InstructionData[InstructionUnion]] = Field(
        ...,
        description="List of instruction data for the generator",
    )
    initial_pitch: int = Field(
        ...,
        description="Reference pitch the generator's arpeggio envelope is measured against",
    )
    held_features: List[FeatureKey] = Field(
        ...,
        description="Dimensions the channel governs, keeping the value it holds while the generator sounds",
    )

    @classmethod
    def create(
        cls,
        generator_name: GeneratorName,
        instructions: List[InstructionUnion],
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
    ) -> InstructionsItem:
        return InstructionsItem(
            generator_name=generator_name,
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
