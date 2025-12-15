from typing import Dict, List, Tuple, Union

import numpy as np

from sampletones.constants.enums import FeatureKey
from sampletones.constants.general import MAX_VOLUME, MIN_PITCH
from sampletones.generators import GeneratorTypeUnion, TriangleGenerator
from sampletones.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    TriangleInstruction,
)
from sampletones.typehints import FeatureMap

from .exporter import Exporter


class TriangleExporter(Exporter[TriangleInstruction]):
    _ATTRIBUTE_MAP: Dict[FeatureKey, InstructionFields] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "pitch",
    }

    @staticmethod
    def extract_data(instructions: List[TriangleInstruction]) -> Tuple[int, List[int], List[int]]:
        initial_pitch = None

        pitch = MIN_PITCH
        volume = 0

        pitches: List[int] = []
        volumes: List[int] = []

        for instruction in instructions:
            if instruction.on:
                if initial_pitch is None:
                    initial_pitch = instruction.pitch
                    pitches = [initial_pitch for _ in range(len(pitches))]

                pitch = instruction.pitch
                volume = MAX_VOLUME
            else:
                volume = 0

            pitches.append(pitch)
            volumes.append(volume)

        if volume > 0:
            volumes.append(0)

        initial_pitch = initial_pitch if initial_pitch is not None else MIN_PITCH
        return initial_pitch, pitches, volumes

    @staticmethod
    def get_feature_map(instructions: List[TriangleInstruction]) -> FeatureMap:
        initial_pitch, pitches, volumes = TriangleExporter.extract_data(instructions)
        arpeggio = np.array(pitches) - initial_pitch

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
        }

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> TriangleInstruction:
        pitch = int(initial_pitch + dictionary["pitch"])
        if not cls.is_pitch_valid(pitch):
            return TriangleInstruction.null_instruction()

        return TriangleInstruction(
            on=cls._infer_instruction_on(dictionary),
            pitch=pitch,
        )

    @staticmethod
    def get_instruction_type() -> InstructionTypeUnion:
        return TriangleInstruction

    @staticmethod
    def get_generator_type() -> GeneratorTypeUnion:
        return TriangleGenerator
