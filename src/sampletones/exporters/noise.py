from typing import Dict, List, Tuple, Union

import numpy as np

from sampletones.constants.enums import FeatureKey
from sampletones.constants.general import NUM_PERIODS
from sampletones.generators import GeneratorTypeUnion, NoiseGenerator
from sampletones.instructions import InstructionFields, InstructionTypeUnion, NoiseInstruction
from sampletones.types.feature import FeatureMap

from .exporter import Exporter


class NoiseExporter(Exporter[NoiseInstruction]):
    _ATTRIBUTE_MAP: Dict[FeatureKey, InstructionFields] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "period",
        FeatureKey.DUTY_CYCLE: "short",
    }

    @classmethod
    def extract_data(cls, instructions: List[NoiseInstruction]) -> Tuple[int, List[int], List[int], List[int]]:
        initial_period = None

        period = 0
        volume = 0
        duty_cycle = 0

        periods: List[int] = []
        volumes: List[int] = []
        duty_cycles: List[int] = []

        for instruction in instructions:
            if instruction.on:
                if initial_period is None:
                    initial_period = instruction.period
                    periods = [initial_period for _ in range(len(periods))]

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

        initial_period = initial_period if initial_period is not None else 0
        return initial_period, periods, volumes, duty_cycles

    @classmethod
    def get_feature_map(cls, instructions: List[NoiseInstruction]) -> FeatureMap:
        initial_period, periods, volumes, duty_cycles = cls.extract_data(instructions)
        arpeggio = (np.array(periods) - initial_period) % NUM_PERIODS

        return {
            FeatureKey.INITIAL_PITCH: initial_period,
            FeatureKey.VOLUME: np.array(volumes).astype(np.int8),
            FeatureKey.ARPEGGIO: arpeggio.astype(np.int8),
            FeatureKey.DUTY_CYCLE: np.array(duty_cycles).astype(np.int8),
        }

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> NoiseInstruction:
        return NoiseInstruction(
            on=cls._infer_instruction_on(dictionary),
            period=int((initial_pitch + dictionary["period"]) % NUM_PERIODS),
            volume=int(dictionary["volume"]),
            short=bool(dictionary["short"]),
        )

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return NoiseInstruction

    @classmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        return NoiseGenerator
