from __future__ import annotations

import struct
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Self, Sequence
from uuid import uuid4

import numpy as np
from pydantic import ConfigDict, Field, ValidationError, field_serializer

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import DataModel, Metadata
from sampletones_core.exporters import (
    INSTRUCTION_TO_EXPORTER_MAP,
    ExporterTypeUnion,
    ExporterUnion,
    Features,
)
from sampletones_core.generators.maps import GENERATOR_CLASSES
from sampletones_core.instructions import InstructionUnion
from sampletones_shared.application import (
    SAMPLETONES_NAME,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from sampletones_shared.deployment.version import compare_versions
from sampletones_shared.exceptions import (
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionValuesError,
    SampleToNESError,
    UnhandledReconstructionError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import Callback
from sampletones_shared.types.data import SerializedData
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.arrays import pad
from sampletones_shared.utils.serialization import load_binary, serialize_array

from ..reconstructor.state import ReconstructionState
from .approximations import ApproximationsItem
from .instructions import InstructionsItem


class Reconstruction(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata = Field(default_factory=Metadata.default, description="Reconstruction metadata")
    id: str = Field(..., description="Unique identifier for the reconstruction")
    audio_filepath: Optional[Path] = Field(
        ...,
        description="Location of the source audio; None marks a reconstruction detached from its local origin",
    )
    config: Config = Field(..., description="Configuration used for reconstruction", frozen=True)
    approximation: np.ndarray = Field(..., description="Audio approximation")
    approximations_data: List[ApproximationsItem] = Field(..., description="Approximations per generator")
    instructions_data: List[InstructionsItem] = Field(..., description="Instructions per generator")
    coefficient: float = Field(..., description="Normalization coefficient used during reconstruction")

    @cached_property
    def approximations(self) -> Dict[GeneratorName, np.ndarray]:
        return {item.generator_name: item.approximation for item in self.approximations_data}

    @cached_property
    def instructions(self) -> Dict[GeneratorName, List[InstructionUnion]]:
        return {
            item.generator_name: [instruction.instruction for instruction in item.instructions]
            for item in self.instructions_data
        }

    @staticmethod
    def _get_exporter_class(instruction: InstructionUnion) -> ExporterTypeUnion:
        return INSTRUCTION_TO_EXPORTER_MAP[type(instruction)]

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
            ApproximationsItem(generator_name=name, approximation=approximation)
            for name, approximation in approximations.items()
        ]

        instructions_data: List[InstructionsItem] = []
        for generator_name, instructions_list in instructions.items():
            instructions_data.append(
                InstructionsItem.create(
                    generator_name=generator_name,
                    instructions=list(instructions_list),
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
        approximation = cls._sum_approximations(list(approximations.values()))

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
    ) -> None:
        partial_approximation = np.trim_zeros(partial_approximation, trim="b")
        max_length = max(
            len(partial_approximation),
            *(len(np.trim_zeros(audio, trim="b")) for audio in self.approximations.values()),
        )

        rendered = {
            name: partial_approximation if name == generator_name else audio
            for name, audio in self.approximations.items()
        }
        self.approximations_data = self._build_approximations_data(rendered, max_length)
        self.instructions_data = [
            (
                InstructionsItem.create(generator_name=generator_name, instructions=instructions)
                if item.generator_name == generator_name
                else item
            )
            for item in self.instructions_data
        ]
        self._invalidate_derived_caches(self)
        self.approximation = self._sum_approximations([item.approximation for item in self.approximations_data])

    def get_generator_instructions(
        self,
        generator_name: GeneratorName,
    ) -> List[InstructionUnion]:
        return self.instructions.get(generator_name, [])

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

        library = self.config.library.model_copy(update={"nes_frequency": nes_frequency})
        config = self.config.model_copy(update={"library": library})
        return self._resynthesized(config)

    def _resynthesized(self, config: Config) -> Reconstruction:
        """Re-renders every generator's approximation from its instructions at ``config``.

        Each instruction spans ``config.frame_length`` samples, so re-rendering at a new frame
        length re-times the audio. Per-generator arrays are padded to a common length and summed;
        the mixer weight is baked into each generator's output, so a plain sum reproduces the
        stored approximation shape. Drive is left at unity to match the regeneration path.
        """
        rendered: Dict[GeneratorName, np.ndarray] = {}
        for generator_name, instructions in self.instructions.items():
            generator = GENERATOR_CLASSES[generator_name](config, generator_name.value)
            if instructions:
                rendered[generator_name] = np.concatenate(
                    [generator(instruction, save=True) for instruction in instructions]  # type: ignore[arg-type]
                )
            else:
                rendered[generator_name] = np.zeros(0, dtype=np.float32)

        max_length = max((len(audio) for audio in rendered.values()), default=0)
        approximations_data = self._build_approximations_data(rendered, max_length)
        approximation = self._sum_approximations([item.approximation for item in approximations_data])

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
    def _sum_approximations(arrays: Sequence[np.ndarray]) -> np.ndarray:
        """Mixes equal-length per-generator approximations into one waveform.

        Returns an empty float array when no generator contributes, so a reconstruction with no
        rendered audio still carries a valid approximation.
        """
        if not arrays:
            return np.zeros(0, dtype=np.float32)

        mixed: np.ndarray = np.sum(np.array(arrays), axis=0).astype(np.float32)
        return mixed

    @staticmethod
    def _build_approximations_data(
        rendered: Mapping[GeneratorName, np.ndarray],
        length: int,
    ) -> List[ApproximationsItem]:
        """Pads each generator's audio to ``length`` and pairs it with its generator name.

        A shared length lets the per-generator arrays stack and sum into the mixed approximation.
        """
        return [
            ApproximationsItem(
                generator_name=name,
                approximation=pad(audio, 0, length),
            )
            for name, audio in rendered.items()
        ]

    @staticmethod
    def _invalidate_derived_caches(reconstruction: Reconstruction) -> None:
        """Drops the memoized per-generator views so they recompute from their backing data."""
        reconstruction.__dict__.pop("approximations", None)
        reconstruction.__dict__.pop("instructions", None)

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

        application_metadata = metadata.application_name
        if application_metadata != SAMPLETONES_NAME:
            raise InvalidMetadataError(
                f"Metadata application name mismatch: expected {SAMPLETONES_NAME}, got {application_metadata}"
            )

        reconstruction_version = metadata.reconstruction_data_version
        if compare_versions(reconstruction_version, SAMPLETONES_RECONSTRUCTION_DATA_VERSION) != 0:
            raise IncompatibleReconstructionVersionError(
                f"Reconstruction data version mismatch: expected "
                f"{SAMPLETONES_RECONSTRUCTION_DATA_VERSION}, got {reconstruction_version}.",
                expected_version=SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
                actual_version=reconstruction_version,
            )

    def _validate_instructions(self, exporter: ExporterUnion, instructions: List[InstructionUnion]) -> None:
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
        features: Dict[GeneratorName, Features] = {}
        for name, instructions in self.instructions.items():
            if not instructions:
                continue

            exporter_class = self._get_exporter_class(instructions[0])
            exporter: ExporterUnion = exporter_class()
            self._validate_instructions(exporter, instructions)
            feature: Features = exporter.to_features(instructions)  # type: ignore[arg-type]
            features[name] = feature

        return features

    @field_serializer("approximation")
    def _serialize_approximation(self, approximation: np.ndarray, _info: Any) -> SerializedData:
        return serialize_array(approximation)

    @field_serializer("audio_filepath")
    def _serialize_audio_filepath(self, audio_filepath: Optional[Path], _info: Any) -> Optional[str]:
        if audio_filepath is None:
            return None

        return str(audio_filepath)
