from __future__ import annotations

import struct
from functools import cached_property
from pathlib import Path
from typing import (
    AbstractSet,
    Dict,
    Final,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Self,
    Sequence,
    Tuple,
)
from uuid import uuid4

import numpy as np
from pydantic import ConfigDict, Field, ValidationError, model_validator

from sampletones_core.audio.mixing import mix
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import upgrade_binary
from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_STEM_ID
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.data import DataModel, Metadata, MetadataContract
from sampletones_core.exporters import (
    CHANNEL_TO_EXPORTER_MAP,
    INSTRUCTION_TO_EXPORTER_MAP,
    ExporterTypeUnion,
    ExporterUnion,
    Features,
)
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_core.reconstructions.reconstruction.rendering import render_streams
from sampletones_core.reconstructions.reconstruction.stems.channel_assignment import ChannelAssignment
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstruction.stems.filter import heard_instructions
from sampletones_core.reconstructions.reconstruction.stems.ownership import UNRECORDED_STEM_IDS, carried_edit
from sampletones_core.reconstructions.reconstruction.stems.selection import StemSelection
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_shared.application import SAMPLETONES_RECONSTRUCTION_DATA_VERSION
from sampletones_shared.exceptions import (
    IncompatibleReconstructionVersionError,
    InvalidReconstructionValuesError,
    SampleToNESError,
    UnhandledReconstructionError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import Callback
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_binary

RECONSTRUCTION_DATA_CONTRACT: Final[MetadataContract] = MetadataContract(
    label="Reconstruction data",
    expected_version=SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
    error=IncompatibleReconstructionVersionError,
)


class Reconstruction(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata = Field(
        default_factory=Metadata.default,
        description="Reconstruction metadata",
    )
    id: str = Field(
        ...,
        description="Unique identifier for the reconstruction",
    )
    config: Config = Field(
        ...,
        description="Configuration used for reconstruction",
        frozen=True,
    )
    instructions_data: List[InstructionsItem] = Field(
        ...,
        description="Instructions per channel",
    )
    stems_data: StemsData = Field(
        ...,
        description="The stems setup and per-frame assignment recorded by the conversion",
    )
    coefficient: float = Field(
        ...,
        description="Normalization coefficient used during reconstruction",
    )

    @model_validator(mode="after")
    def _validate_record_answers_for_the_channels(self) -> Self:
        """Holds the per-frame record to the channels it describes.

        The record answers for the channels in play and for those alone, names one owner per
        frame of each, and states silence and rest over the same frames. A frame a recording
        holds lies on a channel that recording's settings occupy, while a frame the reader
        wrote answers to no settings.

        Raises:
            ValueError: If the record names channels other than those in play, if a channel's
                owners and frames differ in number, if a frame's owner names neither a recorded
                entry nor rest nor the reader, if rest and silence name different frames, or if
                a recording holds a channel its settings leave out.
        """
        entries = self.stems_data.config.entries_by_id
        owned = self.stems_data.assignments_by_channel
        playing = frozenset(self.playing_channels)
        if frozenset(owned) != playing:
            raise ValueError(f"The stems record names {sorted(owned)} where {sorted(playing)} play")

        for channel_name in playing:
            stream = self.instructions[channel_name]
            stem_ids = owned[channel_name]
            if len(stem_ids) != len(stream):
                raise ValueError(
                    f"The stems record gives {channel_name} {len(stem_ids)} owners for {len(stream)} frames"
                )

            for frame, (instruction, stem_id) in enumerate(zip(stream, stem_ids)):
                self._validate_frame_owner(channel_name, frame, instruction, stem_id, entries)

        return self

    @staticmethod
    def _validate_frame_owner(
        channel_name: ChannelName,
        frame: int,
        instruction: InstructionUnion,
        stem_id: int,
        entries: Mapping[int, StemEntry],
    ) -> None:
        """Holds one frame's owner to the record's rules.

        Raises:
            ValueError: If the owner names nothing the setup knows, if rest and silence disagree,
                or if a recording holds a channel its settings leave out.
        """
        if stem_id not in entries and stem_id not in UNRECORDED_STEM_IDS:
            raise ValueError(f"Frame {frame} of {channel_name} names stem {stem_id}, which the setup leaves out")

        if (stem_id == RESTING_STEM_ID) != (not instruction.on):
            raise ValueError(f"Frame {frame} of {channel_name} states rest and silence over different frames")

        if stem_id in entries and channel_name not in entries[stem_id].settings.channel_set:
            raise ValueError(f"Frame {frame} gives stem {stem_id} the {channel_name} its settings leave out")

    @property
    def audio_filepath(self) -> Tuple[Path, ...]:
        """Where the recordings behind this document live, in entry order.

        The record names each recording and the file it was read from, so this reads the
        locations off it: one path per recording while every one of them is still located, and
        none at all once the document is detached from its origin.
        """
        return self.stems_data.paths

    @cached_property
    def approximations(self) -> Dict[ChannelName, np.ndarray]:
        """The audio each channel in play renders, at the drive its owner gives each frame.

        A reconstruction records the instructions a channel plays and the recording behind each
        of its frames, so its sound is read from those rather than carried beside them. Reading
        it here keeps one answer for the waveform, playback, an export and the mixed
        approximation, and keeps a stored document to what it describes.
        """
        return render_streams(self.instructions, self.stems_data, self.config)

    @cached_property
    def approximation(self) -> np.ndarray:
        """The whole reconstruction, summed from the channels that play."""
        return mix(list(self.approximations.values()))

    @cached_property
    def streams(self) -> Dict[ChannelName, InstructionsItem]:
        """The instruction stream each channel carries, in channel order.

        This is where the channel set is made whole: a channel the stored data names a stream
        for keeps it, and one it names none for rests, which is what a channel standing by
        carries. Every per-channel view reads from here, so each of them covers the four
        channels however a reconstruction reached memory.
        """
        stored = {item.channel_name: item for item in self.instructions_data}
        return {
            channel_name: stored.get(channel_name, InstructionsItem.resting(channel_name))
            for channel_name in ChannelName.items()
        }

    @cached_property
    def instructions(self) -> Dict[ChannelName, List[InstructionUnion]]:
        return {
            channel_name: [instruction.instruction for instruction in item.instructions]
            for channel_name, item in self.streams.items()
        }

    @cached_property
    def initial_pitches(self) -> Dict[ChannelName, int]:
        """The reference pitch each channel's arpeggio envelope is measured against."""
        return {channel_name: item.initial_pitch for channel_name, item in self.streams.items()}

    @cached_property
    def held_features(self) -> Dict[ChannelName, Tuple[FeatureKey, ...]]:
        """The dimensions each channel's instrument writes for itself.

        An instruction states every dimension of its frame, so which of them the instrument
        itself writes is stated here: the rest are the channel's, and an export leaves their
        envelopes empty for the player to fill from the value it holds.
        """
        return {channel_name: tuple(item.held_features) for channel_name, item in self.streams.items()}

    @cached_property
    def playing_channels(self) -> Tuple[ChannelName, ...]:
        """The channels whose instruction stream describes a frame.

        A reconstruction holds a stream for every channel, so this is what says which of them
        play: the rest stand by, exporting nothing and costing nothing, while describing a
        frame is what puts one in play.
        """
        return tuple(channel_name for channel_name, item in self.streams.items() if item.instructions)

    @staticmethod
    def _get_exporter_class(instruction: InstructionUnion) -> ExporterTypeUnion:
        return INSTRUCTION_TO_EXPORTER_MAP[type(instruction)]

    @classmethod
    def _exporter_class(
        cls,
        channel_name: ChannelName,
        instructions: List[InstructionUnion],
    ) -> ExporterTypeUnion:
        """The exporter a channel's stream is read through.

        The instruction type names the exporter wherever the stream describes a frame; a
        channel standing by takes the exporter its channel name pairs with.
        """
        if not instructions:
            return CHANNEL_TO_EXPORTER_MAP[channel_name]

        return cls._get_exporter_class(instructions[0])

    @classmethod
    def _derive_initial_pitch(cls, instructions: List[InstructionUnion]) -> int:
        """Chooses the reference pitch the arpeggio envelope of a channel in play is measured against.

        The instruction type selects the exporter, matching how `export` resolves one.
        """
        exporter_class = cls._get_exporter_class(instructions[0])
        return exporter_class.derive_initial_pitch(instructions)  # type: ignore[arg-type]

    @classmethod
    def create(
        cls,
        instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
        config: Config,
        coefficient: float,
        audio_filepath: Tuple[Path, ...],
        stems_data: StemsData,
    ) -> Self:
        instructions_data: List[InstructionsItem] = []
        for channel_name in ChannelName.items():
            channel_instructions = list(instructions.get(channel_name, ()))
            if not channel_instructions:
                instructions_data.append(InstructionsItem.resting(channel_name))
                continue

            exporter_class = cls._get_exporter_class(channel_instructions[0])
            instructions_data.append(
                InstructionsItem.create(
                    channel_name=channel_name,
                    instructions=channel_instructions,
                    initial_pitch=cls._derive_initial_pitch(channel_instructions),
                    held_features=exporter_class.unstated_features(channel_instructions),  # type: ignore[arg-type]
                )
            )

        return cls(
            id=uuid4().hex,
            instructions_data=instructions_data,
            stems_data=stems_data.with_sources(audio_filepath),
            config=config,
            coefficient=coefficient,
        )

    @classmethod
    def from_state(
        cls,
        state: ReconstructionState,
        config: Config,
        coefficient: float,
        path: Tuple[Path, ...],
        stems_data: StemsData,
    ) -> Optional[Self]:
        if all(not stream for stream in state.instructions.values()):
            logger.warning(f"Reconstruction for file: {path} is empty")
            return None

        return cls.create(
            instructions=state.instructions,
            config=config,
            coefficient=coefficient,
            audio_filepath=path,
            stems_data=stems_data,
        )

    def update_channel_data(
        self,
        channel_name: ChannelName,
        instructions: List[InstructionUnion],
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
        *,
        heard: AbstractSet[int],
    ) -> None:
        """Replaces one channel's instructions, reference pitch, and held dimensions.

        The reference pitch travels with the instructions it produced, so a later export
        measures the arpeggio against the same base the edit was made from. The held
        dimensions travel with them for the same reason: the frames state a value for every
        dimension, and this is what says which of them the instrument itself wrote.

        The record follows the frames: each of them keeps the recording that held it, one the
        edit quiets rests, and one it brings into play is the reader's own. ``heard`` names the
        recordings the edit reaches on this channel, so a frame of a recording left out of it
        stands as it is. A channel the edit clears of every frame stands by and stays editable;
        its audio is read afresh from the stream it now carries.

        Args:
            channel_name: The channel the edit writes.
            instructions: The stream the edit offers, one instruction per frame.
            initial_pitch: The reference pitch the channel's arpeggio is measured against.
            held_features: The dimensions the channel governs.
            heard: The recordings the reader hears on this channel, which the edit reaches.
        """
        carried = carried_edit(
            self.instructions[channel_name],
            self.stems_data.assignments_by_channel.get(channel_name, ()),
            instructions,
            heard=heard,
        )

        streams = dict(self.streams)
        streams[channel_name] = InstructionsItem.create(
            channel_name=channel_name,
            instructions=carried.instructions,
            initial_pitch=initial_pitch,
            held_features=held_features,
        )
        self.instructions_data = [streams[name] for name in ChannelName.items()]
        self.stems_data = StemsData(
            config=self.stems_data.config,
            sources=self.stems_data.sources,
            assignments=self._assignments_with(channel_name, carried.stem_ids),
        )
        self._invalidate_derived_caches(self)

    def _assignments_with(
        self,
        channel_name: ChannelName,
        stem_ids: List[int],
    ) -> List[ChannelAssignment]:
        """The per-channel record with one channel's owners replaced, in channel order.

        A channel the edit leaves with no frame stands by, so it leaves the record along with
        its stream.
        """
        replaced = {item.channel_name: item for item in self.stems_data.assignments}
        if stem_ids:
            replaced[channel_name] = ChannelAssignment(channel_name=channel_name, stem_ids=stem_ids)
        else:
            replaced.pop(channel_name, None)

        return [replaced[name] for name in ChannelName.items() if name in replaced]

    @property
    def recorded_stem_ids(self) -> FrozenSet[int]:
        """The recordings the document was built from, as a scope covering every one of them."""
        return frozenset(self.stems_data.config.entries_by_id)

    def get_channel_instructions(
        self,
        channel_name: ChannelName,
    ) -> List[InstructionUnion]:
        return self.instructions[channel_name]

    def detach_source(self) -> None:
        """Drops the local source-audio location so the reconstruction becomes self-contained.

        Embedding a reconstruction in a project makes it part of a shareable artifact, where an
        absolute path to the author's machine carries no meaning. Letting each recording's
        location go keeps everything the document describes — its instructions, its per-frame
        record and the name of every recording behind it — so a saved project stays portable and
        still says what played where.
        """
        self.stems_data = self.stems_data.detached()

    def with_nes_frequency(self, nes_frequency: int) -> Reconstruction:
        """Returns a copy retuned to ``nes_frequency`` by re-rendering its audio.

        A project runs every embedded sample at one change rate, so a reconstruction joining a
        project adopts that rate. The frozen ``config`` is rebuilt at the new rate and each
        channel's approximation is re-synthesized from its stored instructions at the matching
        frame length, re-timing the audio; the instructions and coefficient carry over. The
        original instance is returned when it already runs at ``nes_frequency``.
        """
        if self.config.nes_frequency == nes_frequency:
            return self

        return self._resynthesized(self.config.with_library(nes_frequency=nes_frequency))

    def _resynthesized(self, config: Config) -> Reconstruction:
        """Returns a copy running at ``config``, which re-times the audio it reads.

        Each instruction spans ``config.frame_length`` samples, so the same instructions read at
        a new frame length sound over a new span. The instructions, the record and the
        coefficient carry over.
        """
        retuned: Reconstruction = self.model_copy(update={"config": config})
        self._invalidate_derived_caches(retuned)
        return retuned

    @staticmethod
    def _invalidate_derived_caches(reconstruction: Reconstruction) -> None:
        """Drops the memoized per-channel views so they recompute from their backing data."""
        reconstruction.__dict__.pop("approximation", None)
        reconstruction.__dict__.pop("approximations", None)
        reconstruction.__dict__.pop("streams", None)
        reconstruction.__dict__.pop("instructions", None)
        reconstruction.__dict__.pop("initial_pitches", None)
        reconstruction.__dict__.pop("held_features", None)
        reconstruction.__dict__.pop("playing_channels", None)

    @classmethod
    def load(cls, path: Pathlike, fast: bool = True) -> Reconstruction:
        binary = load_binary(path)
        return cls.deserialize_data(
            binary,
            source=Path(path),
            validation=cls.validate_metadata,
            fast=fast,
        )

    @classmethod
    def deserialize_data(
        cls,
        binary: bytes,
        source: Pathlike,
        validation: Optional[Callback] = None,
        fast: bool = True,
    ) -> Reconstruction:
        try:
            binary = upgrade_binary(ObjectKind.RECONSTRUCTION, binary)
            return cls.deserialize(binary, validation=validation, fast=fast)
        except (ValidationError, TypeError, ValueError, struct.error, IndexError) as exception:
            raise InvalidReconstructionValuesError(
                f'Failed to deserialize ReconstructionData from "{source}" due to validation error: {exception}',
                exception,
            ) from exception
        except SampleToNESError:
            raise
        except Exception as exception:
            raise UnhandledReconstructionError(
                f'Unhandled reconstruction error while loading "{source}": {exception}'
            ) from exception

    @staticmethod
    def validate_metadata(metadata: Metadata) -> None:
        if not isinstance(metadata, Metadata):
            return

        RECONSTRUCTION_DATA_CONTRACT.validate(
            metadata,
            metadata.reconstruction_data_version,
        )

    def _validate_instructions(
        self,
        exporter: ExporterUnion,
        instructions: List[InstructionUnion],
    ) -> None:
        first_instruction: InstructionUnion = instructions[0]
        exporter_class = self._get_exporter_class(instructions[0])
        exporter_instruction_type = exporter.get_instruction_type()
        for instruction in instructions:
            if not isinstance(instruction, type(first_instruction)):
                raise TypeError(f"All instructions must be of the same type for exporter {exporter_class.__name__}")

            if not isinstance(instruction, exporter_instruction_type):
                raise TypeError(
                    f"Instruction type {type(instruction).__name__} is not compatible "
                    f"with exporter {exporter_class.__name__}"
                )

    def export(self) -> Dict[ChannelName, Features]:
        """The envelopes each channel exports, one entry per channel the reconstruction holds.

        A channel standing by describes no frame, so its envelopes come back empty and every
        reader tells it from a channel that plays by :attr:`Features.has_frames`.

        Returns:
            Dict[ChannelName, Features]: The envelope representation of each channel.
        """
        return self._features_of(self.instructions)

    def export_heard(self, selection: StemSelection) -> Dict[ChannelName, Features]:
        """The envelopes of the part each channel plays for the recordings a reader hears.

        The reading the waveform draws and the one an instrument is written from are the same
        one, so what stands on screen is what an export writes. A channel every recording is
        left out on describes no frame, which reads as standing by.

        Args:
            selection: The recordings the reader hears, channel by channel.

        Returns:
            Dict[ChannelName, Features]: The heard envelopes of each channel.
        """
        return self._features_of(heard_instructions(self.stems_data, self.instructions, selection))

    def _features_of(
        self,
        instructions: Mapping[ChannelName, Sequence[InstructionUnion]],
    ) -> Dict[ChannelName, Features]:
        """The envelopes a set of streams exports, each read through the exporter its type names."""
        features: Dict[ChannelName, Features] = {}
        for name in ChannelName.items():
            stream = list(instructions[name])
            exporter_class = self._exporter_class(name, stream)
            exporter: ExporterUnion = exporter_class()
            if stream:
                self._validate_instructions(exporter, stream)

            features[name] = exporter.to_features(
                stream,  # type: ignore[arg-type]
                self.initial_pitches[name],
                self.held_features[name],
            )

        return features
