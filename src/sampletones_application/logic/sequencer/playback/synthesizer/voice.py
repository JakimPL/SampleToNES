from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import GENERATOR_NAME_TO_EXPORTER_MAP, ExporterTypeUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class SampleVoice:
    """How one channel reads a sample's frames.

    A sample carries a frame per tick stating every dimension the channel reads, and the
    reconstruction names which of those dimensions the instrument itself wrote. The rest are the
    channel's own: the instrument leaves an empty envelope for them and the channel sounds them at
    the value it holds, which is what clearing an envelope in the instruments panel means once the
    sample is played in a song.

    Attributes:
        exporter: The reading that turns this channel's frames into envelope values and back.
        initial_pitch: Reference pitch the arpeggio values are measured against.
        held_features: The dimensions the instrument leaves to the channel.
    """

    exporter: ExporterTypeUnion
    initial_pitch: int
    held_features: Tuple[FeatureKey, ...]

    @classmethod
    def read(
        cls,
        reconstruction: Reconstruction,
        generator_name: GeneratorName,
    ) -> SampleVoice:
        """The voice one channel of ``reconstruction`` is played through.

        Args:
            reconstruction: The sample's reconstruction.
            generator_name: The channel being sounded.

        Returns:
            SampleVoice: The reading of that channel's frames.
        """
        return cls(
            exporter=GENERATOR_NAME_TO_EXPORTER_MAP[generator_name],
            initial_pitch=reconstruction.initial_pitches[generator_name],
            held_features=reconstruction.held_features[generator_name],
        )

    def sound(
        self,
        instruction: InstructionUnion,
        feature_values: Dict[FeatureKey, int],
    ) -> InstructionUnion:
        """The frame the channel sounds, once the dimensions it governs are filled in.

        ``feature_values`` is the channel's own, and this is where it moves: the dimensions the
        frame states and the instrument writes are handed over to it, and every dimension the
        frame plays is then read back out of it. So an instrument that writes a dimension sets
        what the channel holds, and one that leaves it empty sounds at what the channel holds.

        Args:
            instruction: The frame as the sample holds it.
            feature_values: The values the channel holds, updated with what the instrument writes.

        Returns:
            InstructionUnion: The frame to sound, before the pattern's transpose and volume.
        """
        stated = self.exporter.feature_values(
            instruction,  # type: ignore[arg-type]
            self.initial_pitch,
        )
        for feature_key, value in stated.items():
            if feature_key not in self.held_features:
                feature_values[feature_key] = value

        sounded: InstructionUnion = self.exporter.instruction_from_values(
            feature_values,
            self.initial_pitch,
        )
        return sounded
