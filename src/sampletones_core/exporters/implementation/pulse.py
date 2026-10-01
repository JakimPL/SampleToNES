from typing import ClassVar, Dict, List, Tuple, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.implementation.utils import center_pitch
from sampletones_core.generators import GeneratorTypeUnion, PulseGenerator
from sampletones_core.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    PulseInstruction,
)
from sampletones_core.utils.frequencies import played_pitch

from ..tonal import TonalExporter


class PulseExporter(TonalExporter[PulseInstruction]):
    _ATTRIBUTE_MAP: ClassVar[Dict[FeatureKey, InstructionFields]] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "pitch",
        FeatureKey.PITCH: "detune",
        FeatureKey.HI_PITCH: "coarse_detune",
        FeatureKey.DUTY_CYCLE: "duty_cycle",
    }

    @classmethod
    def extract_data(cls, instructions: List[PulseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
        initial_pitch, pitches = cls.read_pitches(instructions)
        volume = 0
        duty_cycle = 0
        volumes: List[int] = []
        duty_cycles: List[int] = []

        for instruction in instructions:
            volume = instruction.volume if instruction.on else 0
            duty_cycle = instruction.duty_cycle if instruction.on else duty_cycle
            volumes.append(volume)
            duty_cycles.append(duty_cycle)

        if volume > 0:
            volumes.append(0)

        return initial_pitch, pitches, volumes, duty_cycles

    @classmethod
    def derive_initial_pitch(cls, instructions: List[PulseInstruction]) -> int:
        first_pitch, pitches, _, _ = cls.extract_data(instructions)
        return center_pitch(first_pitch, pitches)

    @classmethod
    def read_envelopes(
        cls,
        instructions: List[PulseInstruction],
        initial_pitch: int,
    ) -> Dict[FeatureKey, Tuple[int, ...]]:
        _, pitches, volumes, duty_cycles = cls.extract_data(instructions)

        return {
            FeatureKey.VOLUME: tuple(volumes),
            FeatureKey.ARPEGGIO: tuple(pitch - initial_pitch for pitch in pitches),
            FeatureKey.DUTY_CYCLE: tuple(duty_cycles),
            **cls.read_bends(instructions),
        }

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> PulseInstruction:
        pitch = played_pitch(int(initial_pitch + dictionary[cls._ATTRIBUTE_MAP[FeatureKey.ARPEGGIO]]))
        return PulseInstruction(
            on=cls._infer_instruction_on(dictionary),
            pitch=pitch,
            volume=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.VOLUME]]),
            duty_cycle=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.DUTY_CYCLE]]),
            **cls.bend_fields(dictionary),
        )

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return PulseInstruction

    @classmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        return PulseGenerator
