from typing import Dict, List, Tuple

import numpy as np

from sampletones.constants.enums import FeatureKey
from sampletones.instructions import NoiseInstruction
from sampletones.typehints import FeatureValue

from .exporter import Exporter


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
        arpeggio = (np.array(periods) - initial_period) % 16

        return {
            FeatureKey.INITIAL_PITCH: initial_period,
            FeatureKey.VOLUME: np.array(volumes),
            FeatureKey.ARPEGGIO: np.array(arpeggio),
            FeatureKey.DUTY_CYCLE: np.array(duty_cycles),
        }
