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

        pitch = MIN_PITCH
        volume = 0

        pitches = []
        volumes = []

        for instruction in instructions:
            if instruction.on:
                if initial_pitch is None:
                    initial_pitch = instruction.pitch
                    for index in range(len(pitches)):
                        pitches[index] = initial_pitch

                pitch = instruction.pitch
                volume = MAX_VOLUME
            else:
                volume = 0

            pitches.append(pitch)
            volumes.append(volume)

        if volume > 0:
            volumes.append(0)

        return initial_pitch or MIN_PITCH, pitches, volumes

    def get_feature_map(self, instructions: List[TriangleInstruction]) -> FeatureMap:
        initial_pitch, pitches, volumes = self.extract_data(instructions)
        arpeggio = np.array(pitches) - initial_pitch

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
        }
