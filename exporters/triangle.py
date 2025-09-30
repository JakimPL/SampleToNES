from typing import Dict, List, Tuple

import numpy as np

from constants import MAX_VOLUME
from exporters.exporter import Exporter, FeatureKey, FeatureValue
from instructions.triangle import TriangleInstruction


class TriangleExporter(Exporter):
    def extract_data(self, instructions: List[TriangleInstruction]) -> Tuple[int, List[int], List[int]]:
        initial_pitch = None
        initial_timer = None

        timer_value = 0
        volume = 0

        pitches = []
        volumes = []

        for instruction in instructions:
            if instruction.on and instruction.pitch is not None:
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

        return initial_pitch, pitches, volumes

    def get_features(self, instructions: List[TriangleInstruction]) -> Dict[FeatureKey, FeatureValue]:
        initial_pitch, pitches, volumes = self.extract_data(instructions)
        hi_pitches = np.diff(np.array(pitches)) // 16
        pitches = np.diff(np.array(pitches)) % 16

        return {
            "initial_pitch": initial_pitch,
            "volume": np.array(volumes, dtype=np.int8),
            "pitch": np.array(pitches, dtype=np.int8),
            "hi_pitch": np.array(hi_pitches, dtype=np.int8),
        }
