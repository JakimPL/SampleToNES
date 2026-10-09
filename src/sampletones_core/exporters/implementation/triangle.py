from typing import ClassVar, Dict, List, Tuple, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters.implementation.utils import center_pitch
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
    def extract_data(cls, instructions: List[TriangleInstruction]) -> Tuple[int, List[int], List[int]]:
        initial_pitch, pitches = cls.read_pitches(instructions)
        volumes = [MAX_VOLUME if instruction.on else 0 for instruction in instructions]
        if volumes and volumes[-1] > 0:
            volumes.append(0)

        return initial_pitch, pitches, volumes

    @classmethod
    def derive_initial_pitch(
        cls,
        instructions: List[TriangleInstruction],
    ) -> int:
        first_pitch, pitches, _ = cls.extract_data(instructions)
        return center_pitch(first_pitch, pitches)

    @classmethod
    def read_envelopes(
        cls,
        instructions: List[TriangleInstruction],
        initial_pitch: int,
    ) -> Dict[FeatureKey, Tuple[int, ...]]:
        _, pitches, volumes = cls.extract_data(instructions)

        return {
            FeatureKey.VOLUME: tuple(volumes),
            FeatureKey.ARPEGGIO: tuple(pitch - initial_pitch for pitch in pitches),
            **cls.read_bends(instructions),
        }

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
