from typing import ClassVar, Dict, List, Sequence, Tuple, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.exporters.implementation.utils import held_across_rests
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.generators import GeneratorTypeUnion, PulseGenerator
from sampletones_core.instructions import (
    InstructionFields,
    InstructionTypeUnion,
    PulseInstruction,
)
from sampletones_core.utils.frequencies import played_pitch

from ..tonal import TonalExporter


class PulseExporter(TonalExporter[PulseInstruction]):
    _ATTRIBUTE_MAP: ClassVar[Dict[FeatureKey, InstructionFields]] = {
        FeatureKey.VOLUME: "volume",
        FeatureKey.ARPEGGIO: "pitch",
        FeatureKey.PITCH: "detune",
        FeatureKey.HI_PITCH: "coarse_detune",
        FeatureKey.DUTY_CYCLE: "duty_cycle",
    }

    @classmethod
    def volume_of(cls, instruction: PulseInstruction) -> int:
        return instruction.volume

    @classmethod
    def read_duty_cycles(cls, instructions: Sequence[PulseInstruction]) -> Tuple[int, ...]:
        """The duty cycle each frame carries, read the way a contour is: a rest holds the duty the
        last sounding frame stated, and the rests before the first take its duty."""
        return held_across_rests(
            instructions,
            lambda instruction: instruction.duty_cycle,
            CHANNEL_FEATURE_DEFAULTS[FeatureKey.DUTY_CYCLE],
        )

    @classmethod
    def read_envelopes(
        cls,
        instructions: List[PulseInstruction],
        initial_pitch: int,
    ) -> Dict[FeatureKey, Tuple[int, ...]]:
        return {
            **super().read_envelopes(instructions, initial_pitch),
            FeatureKey.DUTY_CYCLE: cls.read_duty_cycles(instructions),
        }

    @classmethod
    def _features_dictionary_to_instruction(
        cls,
        dictionary: Dict[str, Union[bool, int]],
        initial_pitch: int,
    ) -> PulseInstruction:
        pitch = played_pitch(int(initial_pitch + dictionary[cls._ATTRIBUTE_MAP[FeatureKey.ARPEGGIO]]))
        return PulseInstruction(
            on=cls._infer_instruction_on(dictionary),
            pitch=pitch,
            volume=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.VOLUME]]),
            duty_cycle=int(dictionary[cls._ATTRIBUTE_MAP[FeatureKey.DUTY_CYCLE]]),
            **cls.bend_fields(dictionary),
        )

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return PulseInstruction

    @classmethod
    def get_generator_type(cls) -> GeneratorTypeUnion:
        return PulseGenerator
