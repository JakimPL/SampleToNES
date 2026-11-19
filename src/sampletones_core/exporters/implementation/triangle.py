from typing import ClassVar, Dict, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.generators import GeneratorTypeUnion, TriangleGenerator
from sampletones_core.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    TriangleInstruction,
)
from sampletones_core.utils.frequencies import played_pitch

from ..tonal import TonalExporter


class TriangleExporter(TonalExporter[TriangleInstruction]):
    _ATTRIBUTE_MAP: ClassVar[Dict[FeatureKey, InstructionFields]] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "pitch",
        FeatureKey.PITCH: "detune",
        FeatureKey.HI_PITCH: "coarse_detune",
    }

    @classmethod
    def volume_of(cls, instruction: TriangleInstruction) -> int:
        """A sounding triangle plays at the one level its channel has."""
        return MAX_VOLUME

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> TriangleInstruction:
        pitch = played_pitch(int(initial_pitch + dictionary[cls._ATTRIBUTE_MAP[FeatureKey.ARPEGGIO]]))
        return TriangleInstruction(
            on=cls._infer_instruction_on(dictionary),
            pitch=pitch,
            **cls.bend_fields(dictionary),
        )

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return TriangleInstruction

    @classmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        return TriangleGenerator
