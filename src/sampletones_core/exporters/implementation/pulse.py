from typing import Dict, List, Tuple, Union

import numpy as np

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import MIN_PITCH
from sampletones_core.generators import GeneratorTypeUnion, PulseGenerator
from sampletones_core.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    PulseInstruction,
)
from sampletones_core.types.feature import FeatureMap
from sampletones_core.utils.frequencies import is_pitch_valid

from ..exporter import Exporter


class PulseExporter(Exporter[PulseInstruction]):
    _ATTRIBUTE_MAP: Dict[FeatureKey, InstructionFields] = {
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
    def get_feature_map(cls, instructions: List[PulseInstruction]) -> FeatureMap:
        initial_pitch, pitches, volumes, duty_cycles = cls.extract_data(instructions)
        arpeggio = np.array(pitches) - initial_pitch

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
            FeatureKey.DUTY_CYCLE: np.array(duty_cycles).astype(np.int8),
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
