from typing import List, Tuple

import numpy as np

from sampletones.constants.enums import FeatureKey
from sampletones.constants.general import MAX_VOLUME, MIN_PITCH
from sampletones.instructions import TriangleInstruction
from sampletones.typehints import FeatureMap

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

                volume = MAX_VOLUME
            else:
                volume = 0

            pitches.append(timer_value)
            volumes.append(volume)

        if volume > 0:
            volumes.append(0)

        return initial_pitch or MIN_PITCH, pitches, volumes

    def get_feature_map(self, instructions: List[TriangleInstruction]) -> FeatureMap:
        initial_pitch, pitches, volumes = self.extract_data(instructions)
        arpeggio = np.array(np.diff(np.array(pitches)))

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
        }
