from typing import ClassVar, Dict, List, Tuple, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MIN_PITCH
from sampletones_core.exporters.implementation.utils import center_pitch
from sampletones_core.generators import GeneratorTypeUnion, PulseGenerator
from sampletones_core.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    PulseInstruction,
)
from sampletones_core.utils.frequencies import is_pitch_valid

from ..exporter import Exporter


class PulseExporter(Exporter[PulseInstruction]):
    _ATTRIBUTE_MAP: ClassVar[Dict[FeatureKey, InstructionFields]] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "pitch",
        FeatureKey.DUTY_CYCLE: "duty_cycle",
    }

    @classmethod
    def extract_data(cls, instructions: List[PulseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
        initial_pitch = None

        pitch = MIN_PITCH
        volume = 0
        duty_cycle = 0

        pitches: List[int] = []
        volumes: List[int] = []
        duty_cycles: List[int] = []

        for instruction in instructions:
            if instruction.on:
                if initial_pitch is None:
                    initial_pitch = instruction.pitch
                    pitches = [initial_pitch for _ in range(len(pitches))]

                pitch = instruction.pitch
                volume = instruction.volume
                duty_cycle = instruction.duty_cycle
            else:
                volume = 0

            pitches.append(pitch)
            volumes.append(volume)
            duty_cycles.append(duty_cycle)

        if volume > 0:
            volumes.append(0)

        initial_pitch = initial_pitch if initial_pitch is not None else MIN_PITCH
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
        }

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> PulseInstruction:
        pitch = int(initial_pitch + dictionary[cls._ATTRIBUTE_MAP[FeatureKey.ARPEGGIO]])
        if not is_pitch_valid(pitch):
            return PulseInstruction.null_instruction()

        return PulseInstruction(
            on=cls._infer_instruction_on(dictionary),
            pitch=pitch,
            volume=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.VOLUME]]),
            duty_cycle=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.DUTY_CYCLE]]),
        )

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return PulseInstruction

    @classmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        return PulseGenerator
