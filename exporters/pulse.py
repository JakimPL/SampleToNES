from typing import Dict, List, Tuple

import numpy as np

from constants.enums import FeatureKey
from constants.general import MIN_PITCH
from exporters.exporter import Exporter
from instructions.pulse import PulseInstruction
from typehints.feature import FeatureValue


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

                timer_value = self.pitch_to_timer(instruction.pitch)
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

    def get_features(self, instructions: List[PulseInstruction]) -> Dict[FeatureKey, FeatureValue]:
        initial_pitch, pitches, volumes, duty_cycles = self.extract_data(instructions)

        return {
            FeatureKey.INITIAL_PITCH: initial_pitch,
            FeatureKey.VOLUME: np.array(volumes, dtype=np.int8),
            FeatureKey.ARPEGGIO: np.array(np.diff(np.array(pitches)) % 16, dtype=np.int8),
            FeatureKey.HI_PITCH: np.array(np.diff(np.array(pitches)) // 16, dtype=np.int8),
            FeatureKey.DUTY_CYCLE: np.array(duty_cycles, dtype=np.int8),
        }
