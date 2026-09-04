from dataclasses import dataclass, replace
from typing import Dict, FrozenSet, List, Optional

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft.instantaneous import InstantaneousPitch
from sampletones_core.generators import (
    GeneratorUnion,
    PulseGenerator,
    TonalGeneratorUnion,
    TriangleGenerator,
)
from sampletones_core.instructions import PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.decoder.base import Streams
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig

from .smoothing import smoothed

StemRecordings = Dict[int, np.ndarray]
StemIds = Dict[ChannelName, List[int]]


@dataclass(frozen=True)
class PitchRefiner:
    """Bends each chosen note towards where the recording's own fundamental stands.

    The matching stage places every frame on the nearest note of the equal-tempered grid, which is
    as fine as its candidate catalog goes. The hardware is finer than that everywhere below the top
    of its range — a divider step spans well under a cent at the lowest notes — so a note the
    matching chose can be carried closer to the sound it stands for.

    Where it lands is read rather than searched. The transform already carries a phase beside every
    magnitude, and how far that phase turns between two frames states a partial's frequency far
    more finely than the bins are spaced; the note the decoder chose says which bins to read. So a
    frame's bend costs a phase difference over a handful of harmonics, and the candidate catalog,
    the per-frame scoring and the decoder's lattice all stay exactly as they were.

    A frame whose sound is not pitched enough for that reading to mean anything makes no proposal,
    and the run of bends is then settled against a toll on changing, so a stream holds a tuning
    rather than chasing one.

    Which recordings are carried, and on which channels, each stem entry states for itself, so a
    channel a stem leaves alone keeps the note the matching chose.

    Attributes:
        config: The settings the refinement and the render are run under.
        channels: The generator each channel sounds through, which owns the divider geometry.
        stems: The setup the run assigns channels under, which states the bends each stem asks for.
    """

    config: Config
    channels: Dict[ChannelName, GeneratorUnion]
    stems: StemsConfig

    @property
    def active(self) -> bool:
        """Whether this run bends its notes.

        A run keeping the audio each frame was matched on would write a bend it never sounds, so
        the refinement acts where the chosen instructions are rendered afresh and some stem asks
        for a bend.
        """
        return bool(self.stems.bent_channels) and self.config.generation.final_regeneration

    def refine(
        self,
        streams: Streams,
        stem_ids: StemIds,
        recordings: StemRecordings,
    ) -> Streams:
        """The decoded streams with every frame's note bent towards what the recording sounds.

        Args:
            streams: What each channel plays, one candidate per frame.
            stem_ids: The stem each channel took, frame by frame.
            recordings: Each stem's recording, at the level the matching was made on.

        Returns:
            Streams: The streams, each frame carrying the bend its reading settled on.
        """
        if not self.active:
            return streams

        readers = {
            stem_id: self._reader(recording) for stem_id, recording in recordings.items() if self._bends_of(stem_id)
        }
        return {
            channel_name: self._refined(channel_name, stream, stem_ids.get(channel_name, []), readers)
            for channel_name, stream in streams.items()
        }

    def _bends_of(self, stem_id: int) -> FrozenSet[ChannelName]:
        """The channels one stem carries towards its own recording."""
        entry = self.stems.entries_by_id.get(stem_id)
        if entry is None:
            return frozenset()

        return entry.settings.bend_set

    def _reader(self, recording: np.ndarray) -> InstantaneousPitch:
        """The instantaneous-pitch reading of one stem, taken once for every channel that took it."""
        return InstantaneousPitch(
            recording,
            self.config.library.sample_rate,
            self.config.library.frame_length,
        )

    def _refined(
        self,
        channel_name: ChannelName,
        stream: List[ScoredCandidate],
        stem_ids: List[int],
        readers: Dict[int, InstantaneousPitch],
    ) -> List[ScoredCandidate]:
        """One channel's stream, each frame bent to the reading its neighborhood settled on."""
        generator = self.channels[channel_name]
        if not isinstance(generator, (PulseGenerator, TriangleGenerator)):
            return stream

        if channel_name not in self.stems.bent_channels:
            return stream

        settings = self.config.generation.refinement
        proposals = [
            self._proposal(generator, channel_name, candidate, frame, stem_ids, readers)
            for frame, candidate in enumerate(stream)
        ]
        bends = smoothed(
            proposals,
            window=settings.window,
            change_weight=settings.change_weight,
        )
        return [self._bent(candidate, bend) for candidate, bend in zip(stream, bends)]

    def _proposal(
        self,
        generator: TonalGeneratorUnion,
        channel_name: ChannelName,
        candidate: ScoredCandidate,
        frame: int,
        stem_ids: List[int],
        readers: Dict[int, InstantaneousPitch],
    ) -> Optional[int]:
        """The bend one frame's reading asks for, and nothing where it has no reading to give."""
        instruction = candidate.instruction
        if not isinstance(instruction, (PulseInstruction, TriangleInstruction)) or not instruction.on:
            return None

        reader = self._reader_at(channel_name, frame, stem_ids, readers)
        if reader is None:
            return None

        reading = reader.at(frame, generator.sounds_at(instruction.pitch, 0))
        if reading is None or reading.confidence < self.config.generation.refinement.confidence:
            return None

        return generator.bend_towards(instruction.pitch, reading.frequency)

    def _reader_at(
        self,
        channel_name: ChannelName,
        frame: int,
        stem_ids: List[int],
        readers: Dict[int, InstantaneousPitch],
    ) -> Optional[InstantaneousPitch]:
        """The reading behind one frame, where the stem it took asks for this channel to bend."""
        if frame >= len(stem_ids):
            return None

        stem_id = stem_ids[frame]
        if stem_id == RESTING_STEM_ID or channel_name not in self._bends_of(stem_id):
            return None

        return readers.get(stem_id)

    @staticmethod
    def _bent(candidate: ScoredCandidate, bend: int) -> ScoredCandidate:
        """One frame carrying a bend, leaving a frame that stands at its note as it was."""
        instruction = candidate.instruction
        if not isinstance(instruction, (PulseInstruction, TriangleInstruction)) or bend == instruction.detune:
            return candidate

        return replace(candidate, instruction=instruction.model_copy(update={"detune": bend}))
