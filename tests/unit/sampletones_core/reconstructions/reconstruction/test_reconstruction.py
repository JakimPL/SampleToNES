from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, List
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import Metadata
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.application import (
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
)
from sampletones_shared.constants.nes import DEFAULT_NES_FREQUENCY
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
    UnhandledReconstructionError,
)
from tests.conftest import ReconstructionFactory
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import DIRECTORY_READ_ERRORS

_RETUNED_FREQUENCY: Final[int] = DEFAULT_NES_FREQUENCY // 2
_FASTER_FREQUENCY: Final[int] = DEFAULT_NES_FREQUENCY * 2

_AUDIO_LENGTH: Final[int] = 64
_BASE_PITCH: Final[int] = 60
_OCTAVE: Final[int] = 12
_CONTOUR_MIDPOINT: Final[int] = 66
_RESET_PITCH: Final[int] = 48


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _reconstruction(instructions: List[PulseInstruction]) -> Reconstruction:
    return Reconstruction.create(
        approximation=np.zeros(_AUDIO_LENGTH, dtype=np.float32),
        approximations={GeneratorName.PULSE1: np.zeros(_AUDIO_LENGTH, dtype=np.float32)},
        instructions={GeneratorName.PULSE1: instructions},
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


class TestRoundTrip:
    def test_save_load_round_trip(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        path = tmp_path / "demo.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.id == reconstruction.id
        assert loaded.coefficient == reconstruction.coefficient
        assert loaded.audio_filepath == reconstruction.audio_filepath
        assert_array_equal(loaded.approximation, reconstruction.approximation)

    def test_detached_source_round_trips_as_none(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction.detach_source()
        path = tmp_path / "detached.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.audio_filepath is None


class TestDetachSource:
    def test_detach_clears_the_source_location(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()
        assert reconstruction.audio_filepath is not None

        reconstruction.detach_source()

        assert reconstruction.audio_filepath is None


class TestLoadRejectsForeignFiles:
    def test_non_reconstruction_file_raises_load_error(self, tmp_path: Path) -> None:
        foreign = tmp_path / "kick.wav"
        foreign.write_bytes(b"RIFF\x58\xb9\x00\x00WAVEfmt " + b"\x00" * 256)

        with pytest.raises(LoadReconstructionError):
            Reconstruction.load(foreign)

    def test_corrupt_binary_raises_invalid_values(self) -> None:
        with pytest.raises(InvalidReconstructionValuesError):
            Reconstruction.deserialize_data(
                b"garbage-not-a-flatbuffer",
                source="corrupt.stn",
            )


class TestLoadFileAccess(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        make_path: Callable[[Path], Path]

    test_cases = (
        TestCase(
            label="missing_file",
            make_path=lambda root: root / "nope.stn",
            expected=FileNotFoundError,
        ),
        TestCase(
            label="directory",
            make_path=lambda root: root,
            expected=DIRECTORY_READ_ERRORS,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_inaccessible_path_raises(
        self,
        test_case: TestCase,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(test_case.expected):
            Reconstruction.load(test_case.make_path(tmp_path))


class TestMetadataValidation:
    def test_incompatible_version_propagates(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory().model_copy(
            update={
                "metadata": Metadata(reconstruction_data_version="0.0"),
            }
        )
        path = tmp_path / "old.stn"
        reconstruction.save(path)

        with pytest.raises(IncompatibleReconstructionVersionError) as exc_info:
            Reconstruction.load(path)

        assert exc_info.value.actual_version == "0.0"
        assert exc_info.value.expected_version == SAMPLETONES_RECONSTRUCTION_DATA_VERSION

    def test_foreign_application_name_propagates(
        self,
        tmp_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory().model_copy(
            update={
                "metadata": Metadata(application_name="Foreign"),
            }
        )
        path = tmp_path / "foreign.stn"
        reconstruction.save(path)

        with pytest.raises(InvalidMetadataError):
            Reconstruction.load(path)


class TestDeserializeDataWrapping(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        side_effect: Exception

    test_cases = (
        TestCase(
            label="unexpected_wrapped_as_unhandled",
            side_effect=RuntimeError("runtime_error"),
            expected=UnhandledReconstructionError,
        ),
        TestCase(
            label="domain_error_propagates_unchanged",
            side_effect=DeserializationError("missing getter"),
            expected=DeserializationError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_deserialize_data_maps_error(self, test_case: TestCase) -> None:
        with patch.object(
            Reconstruction,
            "deserialize",
            side_effect=test_case.side_effect,
        ):
            with pytest.raises(test_case.expected):
                Reconstruction.deserialize_data(b"x", source="mem")


class TestInitialPitchReference:
    """The reference pitch each channel's arpeggio is measured against is stored, not re-derived.

    Storing it is what keeps an arpeggio edit from moving the base pitch: an edited contour
    carries absolute pitches, so deriving a reference from it again would follow the edit.
    """

    def test_create_anchors_each_generator_to_its_contour(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH), _pulse(_BASE_PITCH + _OCTAVE)])

        assert reconstruction.initial_pitches[GeneratorName.PULSE1] == _CONTOUR_MIDPOINT

    def test_export_measures_the_arpeggio_against_the_stored_reference(self) -> None:
        """An arpeggiated channel exports offsets from the pitch it was anchored at.

        The channel is anchored flat at ``_BASE_PITCH`` and then given a contour an octave
        up on its first frame — the shape an ``12 0`` envelope produces. The export reports
        the stored reference and reads the octave straight back.
        """
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)] * 3)
        arpeggiated = [
            _pulse(_BASE_PITCH + _OCTAVE),
            _pulse(_BASE_PITCH),
            _pulse(_BASE_PITCH),
        ]
        reconstruction.update_generator_data(
            GeneratorName.PULSE1,
            arpeggiated,
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _BASE_PITCH,
        )

        features = reconstruction.export()[GeneratorName.PULSE1]

        assert features.initial_pitch == _BASE_PITCH
        assert features.arpeggio.tolist() == [_OCTAVE, 0]

    def test_update_generator_data_replaces_the_reference(self) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH)])

        reconstruction.update_generator_data(
            GeneratorName.PULSE1,
            [_pulse(_RESET_PITCH)],
            np.ones(_AUDIO_LENGTH, dtype=np.float32),
            _RESET_PITCH,
        )

        assert reconstruction.initial_pitches[GeneratorName.PULSE1] == _RESET_PITCH

    def test_reference_survives_a_save_load_round_trip(self, tmp_path: Path) -> None:
        reconstruction = _reconstruction([_pulse(_BASE_PITCH), _pulse(_BASE_PITCH + _OCTAVE)])
        path = tmp_path / "anchored.stn"

        reconstruction.save(path)
        loaded = Reconstruction.load(path)

        assert loaded.initial_pitches == reconstruction.initial_pitches


class TestWithNesFrequency:
    def test_rebuilds_config(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert retuned.config.nes_frequency == _RETUNED_FREQUENCY
        assert retuned.config.frame_length == round(retuned.config.sample_rate / _RETUNED_FREQUENCY)

    def test_resynthesizes_approximation_length(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)
        faster = reconstruction.with_nes_frequency(_FASTER_FREQUENCY)

        generator_approximation = retuned.approximations[GeneratorName.PULSE1]
        assert len(retuned.approximation) == len(generator_approximation)
        assert len(retuned.approximation) == retuned.config.frame_length
        assert len(faster.approximation) < len(retuned.approximation)

    def test_preserves_instructions(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert retuned.instructions == reconstruction.instructions
        assert retuned.coefficient == reconstruction.coefficient

    def test_leaves_original_untouched(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()
        original_frequency = reconstruction.config.nes_frequency
        original_length = len(reconstruction.approximation)

        reconstruction.with_nes_frequency(_RETUNED_FREQUENCY)

        assert reconstruction.config.nes_frequency == original_frequency
        assert len(reconstruction.approximation) == original_length

    def test_matching_rate_returns_self(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        retuned = reconstruction.with_nes_frequency(reconstruction.config.nes_frequency)

        assert retuned is reconstruction
