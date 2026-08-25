from abc import ABC
from typing import Dict, List, Tuple, TypeVar, Union

from sampletones_core.constants.enums import FeatureKey
from sampletones_core.features import CHANNEL_FEATURE_DEFAULTS
from sampletones_core.instructions import TonalInstruction

from .exporter import Exporter
from .implementation.utils import held_across_rests

TonalInstructionT = TypeVar("TonalInstructionT", bound=TonalInstruction)


class TonalExporter(Exporter[TonalInstructionT], ABC):
    """The reading the channels that name a note share: the bend each frame carries.

    A pulse or triangle frame states its note and, beside it, how far off that note's own divider
    it sounds. Both dimensions are read the way a contour is read — a rest carries what the last
    sounding frame stated — so a bend survives a rest exactly as a pitch does.
    """

    @classmethod
    def read_bends(
        cls,
        instructions: List[TonalInstructionT],
    ) -> Dict[FeatureKey, Tuple[int, ...]]:
        """The per-tick values the two bend dimensions carry.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            Dict[FeatureKey, Tuple[int, ...]]: One value per frame for each bend dimension.
        """
        return {
            FeatureKey.PITCH: held_across_rests(
                instructions,
                lambda instruction: instruction.detune,
                CHANNEL_FEATURE_DEFAULTS[FeatureKey.PITCH],
            ),
            FeatureKey.HI_PITCH: held_across_rests(
                instructions,
                lambda instruction: instruction.coarse_detune,
                CHANNEL_FEATURE_DEFAULTS[FeatureKey.HI_PITCH],
            ),
        }

    @classmethod
    def unstated_features(cls, instructions: List[TonalInstructionT]) -> Tuple[FeatureKey, ...]:
        """The bend dimensions this stream makes no use of.

        A stream that never leaves its notes' own dividers has made no bend, which is what a
        channel governing the dimension sounds anyway, so it leaves both dimensions empty.

        Args:
            instructions: The channel's per-frame instructions.

        Returns:
            Tuple[FeatureKey, ...]: The bend dimensions the channel governs, in dimension order.
        """
        written = cls.read_bends(instructions)
        return tuple(
            feature_key
            for feature_key, items in written.items()
            if all(item == CHANNEL_FEATURE_DEFAULTS[feature_key] for item in items)
        )

    @classmethod
    def bend_fields(cls, dictionary: Dict[str, Union[bool, int]]) -> Dict[str, int]:
        """The bend a row of feature values states, as the fields an instruction takes.

        A row naming neither dimension describes a channel that governs both, and a channel holds
        no bend from the start of a song, so the frame sounds at its note's own divider.

        Args:
            dictionary: One frame's feature values, keyed by the instruction field each fills.

        Returns:
            Dict[str, int]: The bend fields to build the instruction with.
        """
        return {
            cls._ATTRIBUTE_MAP[feature_key]: int(
                dictionary.get(
                    cls._ATTRIBUTE_MAP[feature_key],
                    CHANNEL_FEATURE_DEFAULTS[feature_key],
                )
            )
            for feature_key in (FeatureKey.PITCH, FeatureKey.HI_PITCH)
        }
