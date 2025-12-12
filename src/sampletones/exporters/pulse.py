from typing import List, Tuple

import numpy as np

from sampletones.constants.enums import FeatureKey
from sampletones.constants.general import MIN_PITCH
from sampletones.instructions import PulseInstruction
from sampletones.typehints import FeatureMap

from .exporter import Exporter


class PulseExporter(Exporter[PulseInstruction]):
    @staticmethod
    def extract_data(instructions: List[PulseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
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

    @staticmethod
    def get_feature_map(instructions: List[PulseInstruction]) -> FeatureMap:
        initial_pitch, pitches, volumes, duty_cycles = PulseExporter.extract_data(instructions)
        arpeggio = np.array(pitches) - initial_pitch

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
            FeatureKey.DUTY_CYCLE: np.array(duty_cycles).astype(np.int8),
        }

    @staticmethod
    def get_instruction_type() -> type:
        return PulseInstruction
