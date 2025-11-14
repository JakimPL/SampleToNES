from typing import List, Tuple

import numpy as np

from sampletones.constants.enums import FeatureKey
from sampletones.constants.general import MIN_PITCH
from sampletones.instructions import PulseInstruction
from sampletones.typehints import FeatureMap

from .exporter import Exporter


class PulseExporter(Exporter[PulseInstruction]):
    def extract_data(self, instructions: List[PulseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
        initial_pitch = None
        initial_timer = None

        timer_value = 0
        volume = 0
        duty_cycle = 0

        pitches = []
        volumes = []
        duty_cycles = []

        for instruction in instructions:
            if instruction.on:
                if initial_timer is None:
                    initial_pitch = instruction.pitch
                    initial_timer = self.pitch_to_timer(initial_pitch)
                    timer_value = initial_timer
                    pitches.append(timer_value)

                volume = instruction.volume
                duty_cycle = instruction.duty_cycle
            else:
                volume = 0

            pitches.append(timer_value)
            volumes.append(volume)
            duty_cycles.append(duty_cycle)

        if volume > 0:
            volumes.append(0)

        return initial_pitch or MIN_PITCH, pitches, volumes, duty_cycles

    def get_feature_map(self, instructions: List[PulseInstruction]) -> FeatureMap:
        initial_pitch, pitches, volumes, duty_cycles = self.extract_data(instructions)
        arpeggio = np.array(np.diff(np.array(pitches)))

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
            FeatureKey.DUTY_CYCLE: np.array(duty_cycles).astype(np.int8),
        }
