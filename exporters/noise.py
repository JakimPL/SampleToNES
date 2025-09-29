from typing import Dict, List, Tuple

import numpy as np

from constants import MAX_PERIOD
from exporters.exporter import Exporter, FeatureKey, FeatureValue
from instructions.noise import NoiseInstruction


class NoiseExporter(Exporter):
    def get_period(self, instruction: NoiseInstruction) -> int:
        return MAX_PERIOD - instruction.period

    def extract_data(self, instructions: List[NoiseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
        initial_period = None

        period = 0
        volume = 0
        duty_cycle = 0

        periods = []
        volumes = []
        duty_cycles = []

        for instruction in instructions:
            if instruction.on and instruction.period is not None:
                if initial_period is None:
                    initial_period = self.get_period(instruction)
                    period = initial_period
                    periods.append(period)

                period = self.get_period(instruction)
                volume = instruction.volume
                duty_cycle = instruction.mode

            periods.append(period)
            volumes.append(volume)
            duty_cycles.append(duty_cycle)

        return initial_period, periods, volumes, duty_cycles

    def get_features(self, instructions: List[NoiseInstruction]) -> Dict[FeatureKey, FeatureValue]:
        initial_period, periods, volumes, duty_cycles = self.extract_data(instructions)
        arpeggio = np.diff(np.array(periods)) % 16

        return {
            "initial_pitch": initial_period,
            "volume": np.array(volumes, dtype=np.int8),
            "arpeggio": np.array(arpeggio, dtype=np.int8),
            "duty_cycle": np.array(duty_cycles, dtype=np.int8),
        }
