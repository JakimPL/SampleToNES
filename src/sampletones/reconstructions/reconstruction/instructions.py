from __future__ import annotations

from typing import List, Type

from pydantic import ConfigDict, Field

from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel, FlatBufferBuilderProtocol, FlatBufferReaderProtocol
from sampletones.instructions import InstructionData, InstructionUnion


class InstructionsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    instructions: List[InstructionData[InstructionUnion]] = Field(
        ..., description="List of instruction data for the generator"
    )

    @classmethod
    def create(
        cls,
        generator_name: GeneratorName,
        instructions: List[InstructionUnion],
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
        )

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from schemas.reconstruction import FBInstructionsItem

        return FBInstructionsItem

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from schemas.reconstruction import FBInstructionsItem

        return FBInstructionsItem.FBInstructionsItem
