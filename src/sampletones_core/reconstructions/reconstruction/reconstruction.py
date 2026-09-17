from __future__ import annotations

import struct
from functools import cached_property
from pathlib import Path
from typing import (
    Any,
    Dict,
    Final,
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
from pydantic import ConfigDict, Field, ValidationError, field_serializer, model_validator

from sampletones_core.audio.mixing import mix
from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.compatibility.upgrade import upgrade_binary
from sampletones_core.configs import Config
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
from sampletones_core.reconstructions.reconstruction.stems.data import StemsData
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
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
    audio_filepath: Tuple[Path, ...] = Field(
        ...,
        description=(
            "Location of the source audio: one path per stems entry, in entry order, and "
            "empty once detached from the local origin"
        ),
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
    def _validate_source_stem_parallel(self) -> Self:
        if self.audio_filepath and len(self.audio_filepath) != len(self.stems_data.config.entries):
            raise ValueError("The recorded source paths number one per stems entry")

        return self

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
            stems_data=stems_data,
            config=config,
            coefficient=coefficient,
            audio_filepath=audio_filepath,
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
    ) -> None:
        """Replaces one channel's instructions, reference pitch, and held dimensions.

        The reference pitch travels with the instructions it produced, so a later export
        measures the arpeggio against the same base the edit was made from. The held
        dimensions travel with them for the same reason: the frames state a value for every
        dimension, and this is what says which of them the instrument itself wrote.

        The channel keeps its place among the streams however the edit leaves it, so one
        cleared of every frame stands by and stays editable. Its audio is read afresh from the
        stream it now carries.
        """
        streams = dict(self.streams)
        streams[channel_name] = InstructionsItem.create(
            channel_name=channel_name,
            instructions=instructions,
            initial_pitch=initial_pitch,
            held_features=held_features,
        )
        self.instructions_data = [streams[name] for name in ChannelName.items()]
        self.stems_data = StemsData(
            config=self.stems_data.config,
            assignments=[item for item in self.stems_data.assignments if item.channel_name != channel_name],
        )
        self._invalidate_derived_caches(self)

    def get_channel_instructions(
        self,
        channel_name: ChannelName,
    ) -> List[InstructionUnion]:
        return self.instructions[channel_name]

    def detach_source(self) -> None:
        """Drops the local source-audio location so the reconstruction becomes self-contained.

        Embedding a reconstruction in a project makes it part of a shareable artifact, where an
        absolute path to the author's machine carries no meaning. Emptying ``audio_filepath``
        keeps the reconstruction — its approximation and instructions — intact while removing the
        local origin, so a saved project stays portable.
        """
        self.audio_filepath = ()

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
        features: Dict[ChannelName, Features] = {}
        for name in ChannelName.items():
            instructions = self.instructions[name]
            exporter_class = self._exporter_class(name, instructions)
            exporter: ExporterUnion = exporter_class()
            if instructions:
                self._validate_instructions(exporter, instructions)

            features[name] = exporter.to_features(
                instructions,  # type: ignore[arg-type]
                self.initial_pitches[name],
                self.held_features[name],
            )

        return features

    @field_serializer("audio_filepath")
    def _serialize_audio_filepath(
        self,
        audio_filepath: Tuple[Path, ...],
        _info: Any,
    ) -> List[str]:
        return [str(path) for path in audio_filepath]
