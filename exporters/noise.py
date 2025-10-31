from typing import Dict, List, Tuple

import numpy as np

from exporters.exporter import Exporter
from instructions.noise import NoiseInstruction
from typehints.general import FeatureKey, FeatureValue


class NoiseExporter(Exporter[NoiseInstruction]):
    def extract_data(self, instructions: List[NoiseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
        initial_period = None

        period = 0
        volume = 0
        duty_cycle = 0

        periods = []
        volumes = []
        duty_cycles = []

        for instruction in instructions:
            if instruction.on:
                if initial_period is None:
                    initial_period = instruction.period

                period = instruction.period
                volume = instruction.volume
                duty_cycle = instruction.short
            else:
                volume = 0

            periods.append(period)
            volumes.append(volume)
            duty_cycles.append(duty_cycle)

        if volume > 0:
            volumes.append(0)

        return initial_period or 0, periods, volumes, duty_cycles

    def get_features(self, instructions: List[NoiseInstruction]) -> Dict[FeatureKey, FeatureValue]:
        initial_period, periods, volumes, duty_cycles = self.extract_data(instructions)
        arpeggio = (np.array(periods, dtype=np.int16) - initial_period) % 16

        return {
            "initial_pitch": initial_period,
            "volume": np.array(volumes, dtype=np.int8),
            "arpeggio": np.array(arpeggio, dtype=np.int8),
            "duty_cycle": np.array(duty_cycles, dtype=np.int8),
        }
