from typing import Dict, List, Tuple

import numpy as np

from constants.enums import FeatureKey
from constants.general import MAX_VOLUME, MIN_PITCH
from instructions.triangle import TriangleInstruction
from typehints.general import FeatureValue

from .exporter import Exporter


class TriangleExporter(Exporter[TriangleInstruction]):
    def extract_data(self, instructions: List[TriangleInstruction]) -> Tuple[int, List[int], List[int]]:
        initial_pitch = None
        initial_timer = None

        timer_value = 0
        volume = 0

        pitches = []
        volumes = []

        for instruction in instructions:
            if instruction.on:
                if initial_timer is None:
                    initial_pitch = instruction.pitch
                    initial_timer = self.pitch_to_timer(initial_pitch)
                    timer_value = initial_timer
                    pitches.append(timer_value)

                timer_value = self.pitch_to_timer(instruction.pitch)
                volume = MAX_VOLUME
            else:
                volume = 0

            pitches.append(timer_value)
            volumes.append(volume)

        if volume > 0:
            volumes.append(0)

        return initial_pitch or MIN_PITCH, pitches, volumes

    def get_features(self, instructions: List[TriangleInstruction]) -> Dict[FeatureKey, FeatureValue]:
        initial_pitch, pitches, volumes = self.extract_data(instructions)

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes, dtype=np.int8),
            FeatureKey.ARPEGGIO: np.array(np.diff(np.array(pitches)) % 16, dtype=np.int8),
            FeatureKey.HI_PITCH: np.array(np.diff(np.array(pitches)) // 16, dtype=np.int8),
        }
