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
from pydantic import ConfigDict, Field, ValidationError, field_serializer

from sampletones_core.audio.mixing import align, common_length, mix
from sampletones_core.configs import Config
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.data import DataModel, Metadata, MetadataContract
from sampletones_core.exporters import (
    GENERATOR_NAME_TO_EXPORTER_MAP,
    INSTRUCTION_TO_EXPORTER_MAP,
    ExporterTypeUnion,
    ExporterUnion,
    Features,
)
from sampletones_core.generators.render import render_generators
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.application import SAMPLETONES_RECONSTRUCTION_DATA_VERSION
from sampletones_shared.exceptions import (
    IncompatibleReconstructionVersionError,
    InvalidReconstructionValuesError,
    SampleToNESError,
    UnhandledReconstructionError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import Callback
from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_binary, serialize_array

from ..reconstructor.state import ReconstructionState
from .approximations import ApproximationsItem
from .instructions import InstructionsItem

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
    audio_filepath: Optional[Path] = Field(
        ...,
        description="Location of the source audio; None marks a reconstruction detached from its local origin",
    )
    config: Config = Field(
        ...,
        description="Configuration used for reconstruction",
        frozen=True,
    )
    approximation: np.ndarray = Field(
        ...,
        description="Audio approximation",
    )
    approximations_data: List[ApproximationsItem] = Field(
        ...,
        description="Approximations per generator",
    )
    instructions_data: List[InstructionsItem] = Field(
        ...,
        description="Instructions per generator",
    )
    coefficient: float = Field(
        ...,
        description="Normalization coefficient used during reconstruction",
    )

    @cached_property
    def approximations(self) -> Dict[GeneratorName, np.ndarray]:
        return {item.generator_name: item.approximation for item in self.approximations_data}

    @cached_property
    def streams(self) -> Dict[GeneratorName, InstructionsItem]:
        """The instruction stream each channel carries, in channel order.

        This is where the channel set is made whole: a channel the stored data names a stream
        for keeps it, and one it names none for rests, which is what a channel standing by
        carries. Every per-channel view reads from here, so each of them covers the four
        channels however a reconstruction reached memory.
        """
        stored = {item.generator_name: item for item in self.instructions_data}
        return {
            generator_name: stored.get(generator_name, InstructionsItem.resting(generator_name))
            for generator_name in GeneratorName.items()
        }

    @cached_property
    def instructions(self) -> Dict[GeneratorName, List[InstructionUnion]]:
        return {
            generator_name: [instruction.instruction for instruction in item.instructions]
            for generator_name, item in self.streams.items()
        }

    @cached_property
    def initial_pitches(self) -> Dict[GeneratorName, int]:
        """The reference pitch each generator's arpeggio envelope is measured against."""
        return {generator_name: item.initial_pitch for generator_name, item in self.streams.items()}

    @cached_property
    def held_features(self) -> Dict[GeneratorName, Tuple[FeatureKey, ...]]:
        """The dimensions each generator leaves to the channel.

        An instruction states every dimension of its frame, so which of them the instrument
        itself writes is stated here: the rest are the channel's, and an export leaves their
        envelopes empty for the player to fill from the value it holds.
        """
        return {generator_name: tuple(item.held_features) for generator_name, item in self.streams.items()}

    @cached_property
    def playing_generators(self) -> Tuple[GeneratorName, ...]:
        """The channels whose instruction stream describes a frame.

        A reconstruction holds a stream for every channel, so this is what says which of them
        play: the rest stand by, exporting nothing and costing nothing, while describing a
        frame is what puts one in play.
        """
        return tuple(generator_name for generator_name, item in self.streams.items() if item.instructions)

    @staticmethod
    def _get_exporter_class(instruction: InstructionUnion) -> ExporterTypeUnion:
        return INSTRUCTION_TO_EXPORTER_MAP[type(instruction)]

    @classmethod
    def _exporter_class(
        cls,
        generator_name: GeneratorName,
        instructions: List[InstructionUnion],
    ) -> ExporterTypeUnion:
        """The exporter a channel's stream is read through.

        The instruction type names the exporter wherever the stream describes a frame; a
        channel standing by takes the exporter its generator name pairs with.
        """
        if not instructions:
            return GENERATOR_NAME_TO_EXPORTER_MAP[generator_name]

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
        approximation: np.ndarray,
        approximations: Mapping[GeneratorName, np.ndarray],
        instructions: Mapping[GeneratorName, Sequence[InstructionUnion]],
        config: Config,
        coefficient: float,
        audio_filepath: Path,
    ) -> Self:
        approximation = np.nan_to_num(approximation, nan=0.0)
        approximations_data: List[ApproximationsItem] = [
            ApproximationsItem(
                generator_name=generator_name,
                approximation=approximations[generator_name],
            )
            for generator_name in GeneratorName.items()
            if generator_name in approximations
        ]

        instructions_data: List[InstructionsItem] = []
        for generator_name in GeneratorName.items():
            channel_instructions = list(instructions.get(generator_name, ()))
            if not channel_instructions:
                instructions_data.append(InstructionsItem.resting(generator_name))
                continue

            instructions_data.append(
                InstructionsItem.create(
                    generator_name=generator_name,
                    instructions=channel_instructions,
                    initial_pitch=cls._derive_initial_pitch(channel_instructions),
                    held_features=(),
                )
            )

        return cls(
            id=uuid4().hex,
            approximation=approximation,
            approximations_data=approximations_data,
            instructions_data=instructions_data,
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
        path: Path,
    ) -> Optional[Self]:
        if any(len(approximation) == 0 for approximation in state.approximations.values()):
            logger.warning(f"Reconstruction for file: {path} is empty")
            return None

        approximations = {name: np.concatenate(state.approximations[name]) for name in state.approximations}
        approximation = mix(list(approximations.values()))

        return cls.create(
            approximation=approximation,
            approximations=approximations,
            instructions=state.instructions,
            config=config,
            coefficient=coefficient,
            audio_filepath=path,
        )

    def update_generator_data(
        self,
        generator_name: GeneratorName,
        instructions: List[InstructionUnion],
        partial_approximation: np.ndarray,
        initial_pitch: int,
        held_features: Iterable[FeatureKey],
    ) -> None:
        """Replaces one generator's instructions, audio, reference pitch, and held dimensions.

        The reference pitch travels with the instructions it produced, so a later export
        measures the arpeggio against the same base the edit was made from. The held
        dimensions travel with them for the same reason: the frames state a value for every
        dimension, and this is what says which of them the instrument itself wrote.

        The channel keeps its place among the streams however the edit leaves it, so one
        cleared of every frame stands by and stays editable. Its rendered audio lasts as
        long as it carries samples, which keeps silence out of the stored waveforms.
        """
        partial_approximation = np.trim_zeros(partial_approximation, trim="b")
        rendered = {name: audio for name, audio in self.approximations.items() if name != generator_name}
        if partial_approximation.size:
            rendered[generator_name] = partial_approximation

        max_length = max(
            (len(np.trim_zeros(audio, trim="b")) for audio in rendered.values()),
            default=0,
        )

        self.approximations_data = self._build_approximations_data(rendered, max_length)

        streams = dict(self.streams)
        streams[generator_name] = InstructionsItem.create(
            generator_name=generator_name,
            instructions=instructions,
            initial_pitch=initial_pitch,
            held_features=held_features,
        )
        self.instructions_data = [streams[name] for name in GeneratorName.items()]
        self._invalidate_derived_caches(self)
        self.approximation = mix([item.approximation for item in self.approximations_data])

    def get_generator_instructions(
        self,
        generator_name: GeneratorName,
    ) -> List[InstructionUnion]:
        return self.instructions[generator_name]

    def detach_source(self) -> None:
        """Drops the local source-audio location so the reconstruction becomes self-contained.

        Embedding a reconstruction in a project makes it part of a shareable artifact, where an
        absolute path to the author's machine carries no meaning. Clearing ``audio_filepath`` keeps
        the reconstruction — its approximation and instructions — intact while removing the local
        origin, so a saved project stays portable.
        """
        self.audio_filepath = None

    def with_nes_frequency(self, nes_frequency: int) -> Reconstruction:
        """Returns a copy retuned to ``nes_frequency`` by re-rendering its audio.

        A project runs every embedded sample at one change rate, so a reconstruction joining a
        project adopts that rate. The frozen ``config`` is rebuilt at the new rate and each
        generator's approximation is re-synthesized from its stored instructions at the matching
        frame length, re-timing the audio; the instructions and coefficient carry over. The
        original instance is returned when it already runs at ``nes_frequency``.
        """
        if self.config.nes_frequency == nes_frequency:
            return self

        return self._resynthesized(self.config.with_library(nes_frequency=nes_frequency))

    def _resynthesized(self, config: Config) -> Reconstruction:
        """Re-renders every generator's approximation from its instructions at ``config``.

        Each instruction spans ``config.frame_length`` samples, so re-rendering at a new frame
        length re-times the audio. The channels describing frames are rendered, padded to a
        common length and summed; the mixer weight is baked into each generator's output, so a
        plain sum reproduces the stored approximation shape. Drive is left at unity to match the
        regeneration path.
        """
        rendered = render_generators(self.instructions, config)
        approximations_data = self._build_approximations_data(
            rendered,
            common_length(rendered.values()),
        )
        approximation = mix([item.approximation for item in approximations_data])

        retuned: Reconstruction = self.model_copy(
            update={
                "config": config,
                "approximations_data": approximations_data,
                "approximation": approximation,
            }
        )
        self._invalidate_derived_caches(retuned)
        return retuned

    @staticmethod
    def _build_approximations_data(
        rendered: Mapping[GeneratorName, np.ndarray],
        length: int,
    ) -> List[ApproximationsItem]:
        """Brings each rendered channel's audio to ``length``, in channel order.

        A shared length lets the per-generator arrays stack and sum into the mixed approximation,
        and a fixed order keeps a stored reconstruction reading the same however an edit reached it.
        """
        names = [generator_name for generator_name in GeneratorName.items() if generator_name in rendered]
        aligned = align([rendered[generator_name] for generator_name in names], length)
        return [
            ApproximationsItem(
                generator_name=generator_name,
                approximation=audio,
            )
            for generator_name, audio in zip(names, aligned)
        ]

    @staticmethod
    def _invalidate_derived_caches(reconstruction: Reconstruction) -> None:
        """Drops the memoized per-generator views so they recompute from their backing data."""
        reconstruction.__dict__.pop("approximations", None)
        reconstruction.__dict__.pop("streams", None)
        reconstruction.__dict__.pop("instructions", None)
        reconstruction.__dict__.pop("initial_pitches", None)
        reconstruction.__dict__.pop("held_features", None)
        reconstruction.__dict__.pop("playing_generators", None)

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

    def export(self) -> Dict[GeneratorName, Features]:
        """The envelopes each channel exports, one entry per channel the reconstruction holds.

        A channel standing by describes no frame, so its envelopes come back empty and every
        reader tells it from a channel that plays by :attr:`Features.has_frames`.

        Returns:
            Dict[GeneratorName, Features]: The envelope representation of each channel.
        """
        features: Dict[GeneratorName, Features] = {}
        for name in GeneratorName.items():
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

    @field_serializer("approximation")
    def _serialize_approximation(
        self,
        approximation: np.ndarray,
        _info: Any,
    ) -> SerializedData:
        return serialize_array(approximation)

    @field_serializer("audio_filepath")
    def _serialize_audio_filepath(
        self,
        audio_filepath: Optional[Path],
        _info: Any,
    ) -> Optional[str]:
        if audio_filepath is None:
            return None

        return str(audio_filepath)
