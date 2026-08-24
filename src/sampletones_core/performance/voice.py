from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import CHANNEL_TO_EXPORTER_MAP, ExporterTypeUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion, voice_reference


@dataclass(frozen=True)
class VoiceReading:
    """How one channel reads a voice's frames.

    A voice carries a frame per tick stating every dimension the channel reads, and names which of
    those dimensions it writes itself. The rest are the channel's own: the voice leaves an empty
    envelope for them and the channel sounds them at the value it holds, which is what clearing an
    envelope in the instruments panel means once the voice is played in a song.

    Reading a voice on a channel answers all a channel needs of it — the frames, the reference its
    arpeggio is measured against, the dimensions it leaves behind, and what it sounds once the
    written frames run out — so the song walk and the sequencer's renderer read one voice the same
    way.

    Attributes:
        exporter: The reading that turns this channel's frames into envelope values and back.
        instructions: The frames the channel plays, one per tick.
        reference: The pitch the arpeggio values are measured against.
        held_features: The dimensions the voice leaves to the channel.
        channel_name: The channel doing the reading.
        sustaining: The instrument whose envelopes go on past the written frames, where one does.
        loop_point: The frame a recording circles back to, or ``None`` where it plays through once.
    """

    exporter: ExporterTypeUnion
    instructions: Sequence[InstructionUnion]
    reference: int
    held_features: Tuple[FeatureKey, ...]
    channel_name: ChannelName
    sustaining: Optional[Instrument]
    loop_point: Optional[int]

    @classmethod
    def read(
        cls,
        voice: VoiceUnion,
        channel_name: ChannelName,
    ) -> Optional[VoiceReading]:
        """The reading one channel plays ``voice`` through.

        A sample answers with the frames its reconstruction found for this channel and the
        reference they were measured against; an instrument answers with the frames its envelopes
        make of this channel and the pitch it states. Both kinds therefore reach a channel as one
        reading.

        Args:
            voice: The voice being sounded.
            channel_name: The channel sounding it.

        Returns:
            Optional[VoiceReading]: The reading of that channel's frames, or ``None`` where the
                voice describes no frame there and the channel rests.
        """
        sustaining: Optional[Instrument] = None
        loop_point: Optional[int] = None
        match voice:
            case Sample():
                instructions: Sequence[InstructionUnion] = voice.reconstruction.instructions[channel_name]
                held_features = voice.reconstruction.held_features[channel_name]
                loop_point = voice.loop_point
            case Instrument():
                instructions = voice.instructions(channel_name)
                held_features = voice.held_features(channel_name)
                sustaining = voice

        if not instructions:
            return None

        return cls(
            exporter=CHANNEL_TO_EXPORTER_MAP[channel_name],
            instructions=instructions,
            reference=voice_reference(voice, channel_name),
            held_features=held_features,
            channel_name=channel_name,
            sustaining=sustaining,
            loop_point=loop_point,
        )

    def at(self, tick_index: int) -> Optional[InstructionUnion]:
        """The frame standing at ``tick_index`` of a sounding note.

        An instrument goes on past its written frames: each dimension circles from its own loop
        point or holds its last item, so a note sounds for as long as rows keep it sounding and a
        volume envelope ending at silence is what releases it. A recording circles the frames its
        conversion found from the point it states, and the channel rests past the last of them
        where it states none.

        Args:
            tick_index: How many ticks of the voice the channel has played.

        Returns:
            Optional[InstructionUnion]: The frame to sound, or ``None`` where the voice has played
                out and the channel rests.
        """
        if tick_index < len(self.instructions):
            return self.instructions[tick_index]

        if self.sustaining is not None:
            return self.sustaining.instruction_at(self.channel_name, tick_index)

        if self.loop_point is None:
            return None

        point = min(self.loop_point, len(self.instructions) - 1)
        cycle = len(self.instructions) - point
        return self.instructions[point + (tick_index - point) % cycle]

    def sound(
        self,
        instruction: InstructionUnion,
        feature_values: Dict[FeatureKey, int],
    ) -> InstructionUnion:
        """The frame the channel sounds, once the dimensions it governs are filled in.

        ``feature_values`` is the channel's own, and this is where it moves: the dimensions the
        frame states and the voice writes are handed over to it, and every dimension the frame
        plays is then read back out of it. So a voice that writes a dimension sets what the channel
        holds, and one that leaves it empty sounds at what the channel holds.

        Args:
            instruction: The frame as the voice holds it.
            feature_values: The values the channel holds, updated with what the voice writes.

        Returns:
            InstructionUnion: The frame to sound, before the pattern's transpose and volume.
        """
        stated = self.exporter.feature_values(
            instruction,  # type: ignore[arg-type]
            self.reference,
        )
        for feature_key, value in stated.items():
            if feature_key not in self.held_features:
                feature_values[feature_key] = value

        sounded: InstructionUnion = self.exporter.instruction_from_values(
            feature_values,
            self.reference,
        )
        return sounded
