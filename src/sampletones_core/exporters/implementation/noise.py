from typing import ClassVar, Dict, Final, List, Tuple, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.features.spec import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.generators import GeneratorTypeUnion, NoiseGenerator
from sampletones_core.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    NoiseInstruction,
)

from ..exporter import Exporter

SHORT_MODE_BIT: Final[int] = 0x01


class NoiseExporter(Exporter[NoiseInstruction]):
    _ATTRIBUTE_MAP: ClassVar[Dict[FeatureKey, InstructionFields]] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "period",
        FeatureKey.PITCH: "detune",
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
    def derive_initial_pitch(
        cls,
        instructions: List[NoiseInstruction],
    ) -> int:
        initial_period, _, _, _ = cls.extract_data(instructions)
        return initial_period

    @classmethod
    def unstated_features(cls, instructions: List[NoiseInstruction]) -> Tuple[FeatureKey, ...]:
        """Every dimension the noise channel reads is one its frames choose, so it states them all.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            Tuple[FeatureKey, ...]: No dimension, since the stream writes each one it offers.
        """
        return ()

    @classmethod
    def read_envelopes(
        cls,
        instructions: List[NoiseInstruction],
        initial_pitch: int,
    ) -> Dict[FeatureKey, Tuple[int, ...]]:
        _, periods, volumes, duty_cycles = cls.extract_data(instructions)

        return {
            FeatureKey.VOLUME: tuple(volumes),
            FeatureKey.ARPEGGIO: tuple((period - initial_pitch) % NUM_PERIODS for period in periods),
            FeatureKey.DUTY_CYCLE: tuple(duty_cycles),
        }

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> NoiseInstruction:
        """Builds one noise frame from a row of feature values.

        The arpeggio and the bend each move the period one step per unit, around the sixteen
        periods, and the duty cycle's lowest bit selects the short mode. That is how FamiTracker
        and Bitphase read an instrument on noise, and a reconstruction's noise channel, writing no
        bend and a mode of 0 or 1, reads the same either way.

        Args:
            dictionary: The per-attribute values for one frame.
            initial_pitch: The period the arpeggio and the bend are measured against.

        Returns:
            NoiseInstruction: The frame.
        """
        steps = dictionary[cls._ATTRIBUTE_MAP[FeatureKey.ARPEGGIO]] + dictionary.get(
            cls._ATTRIBUTE_MAP[FeatureKey.PITCH],
            CHANNEL_FEATURE_DEFAULTS[FeatureKey.PITCH],
        )
        return NoiseInstruction(
            on=cls._infer_instruction_on(dictionary),
            period=int((initial_pitch + steps) % NUM_PERIODS),
            volume=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.VOLUME]]),
            short=bool(int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.DUTY_CYCLE]]) & SHORT_MODE_BIT),
        )

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return NoiseInstruction

    @classmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        return NoiseGenerator
