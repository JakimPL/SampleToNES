from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, FragmentedAudio, Window
from sampletones_core.generators import MIXER_LEVELS
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.approximation import ApproximationData
from sampletones_core.reconstructions.reconstructor.reconstructor import Reconstructor
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from sampletones_shared.exceptions import NoLibraryDataError


def _make_reconstructor(config: Config, library_data: InstructionLibraryData) -> Reconstructor:
    mock_library = MagicMock()
    mock_library.get.return_value = library_data
    mock_library.create_key.return_value = MagicMock()
    mock_library.get_path.return_value = "test/path"
    return Reconstructor(config, library=mock_library)


class TestReconstructorInit:
    def test_generators_initialized_from_config(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        expected_names = set(config.generation.generators)
        assert set(reconstructor.generators.keys()) == expected_names

    def test_window_created_from_config(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        expected_window = Window.from_config(config)
        assert reconstructor.window.frame_length == expected_window.frame_length
        assert reconstructor.window.size == expected_window.size


class TestReconstructorLoadLibraryError:
    def test_none_library_data_raises_no_library_data_error(self, config: Config) -> None:
        mock_library = MagicMock()
        mock_library.get.return_value = None
        mock_library.create_key.return_value = MagicMock()
        mock_library.get_path.return_value = "test/path"
        with pytest.raises(NoLibraryDataError):
            Reconstructor(config, library=mock_library)


class TestReconstructorGetCoefficient:
    def test_uniform_audio_anchors_to_its_level(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        audio = np.ones(config.library.frame_length, dtype=np.float32) * 0.5
        coefficient = reconstructor.get_coefficient(audio)
        total_mixer = sum(MIXER_LEVELS[gen.class_name()] for gen in reconstructor.generators.values())
        assert coefficient == pytest.approx(0.5 / total_mixer)

    def test_coefficient_is_robust_to_a_lone_transient(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        frame_length = config.library.frame_length
        total_mixer = sum(MIXER_LEVELS[gen.class_name()] for gen in reconstructor.generators.values())
        audio = np.full(frame_length * 24, 0.05, dtype=np.float32)
        audio[:frame_length] = 1.0
        coefficient = reconstructor.get_coefficient(audio)
        assert coefficient == pytest.approx(0.05 / total_mixer, rel=1e-3)
        assert coefficient < 1.0 / total_mixer

    def test_louder_audio_produces_larger_coefficient(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        quiet = np.ones(config.library.frame_length, dtype=np.float32) * 0.1
        loud = np.ones(config.library.frame_length, dtype=np.float32) * 0.9
        assert reconstructor.get_coefficient(loud) > reconstructor.get_coefficient(quiet)


class TestReconstructorGetFragments:
    def test_longer_audio_has_more_fragments(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        short = np.random.randn(config.library.frame_length * 2).astype(np.float32)
        long = np.random.randn(config.library.frame_length * 4).astype(np.float32)
        assert len(reconstructor.get_fragments(short).fragments_ids) < len(
            reconstructor.get_fragments(long).fragments_ids
        )

    def test_each_fragment_audio_length_matches_frame_length(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        audio = np.random.randn(config.library.frame_length * 3).astype(np.float32)
        fragmented = reconstructor.get_fragments(audio)
        for fragment in fragmented.fragments:
            assert len(fragment.audio) == config.library.frame_length


class TestReconstructorResetGenerators:
    def test_reset_clears_generator_states(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        from sampletones_core.generators.implementation.noise import NoiseGenerator
        from sampletones_core.generators.implementation.pulse import PulseGenerator
        from sampletones_core.generators.implementation.triangle import TriangleGenerator
        from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction

        reconstructor = _make_reconstructor(config, library_data)
        for generator in reconstructor.generators.values():
            if isinstance(generator, PulseGenerator):
                generator.save_state(True, PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0))
            elif isinstance(generator, TriangleGenerator):
                generator.save_state(True, TriangleInstruction(on=True, pitch=60))
            elif isinstance(generator, NoiseGenerator):
                generator.save_state(True, NoiseInstruction(on=True, period=0, volume=10, short=False))

        assert all(gen.previous_instruction is not None for gen in reconstructor.generators.values())
        reconstructor.reset_generators()
        assert all(gen.previous_instruction is None for gen in reconstructor.generators.values())


class TestReconstructorUpdateState:
    def _setup(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        final_regeneration: bool,
    ) -> tuple:
        updated_config = config.model_copy(
            update={
                "generation": config.generation.model_copy(
                    update={
                        "final_regeneration": final_regeneration,
                    }
                )
            }
        )
        reconstructor = _make_reconstructor(updated_config, library_data)
        generator_name = next(iter(reconstructor.generators))
        instruction = next(
            instrument
            for instrument, frag in library_data.data.items()
            if frag.generator_class == reconstructor.generators[generator_name].class_name() and instrument.on
        )
        approximation_data = ApproximationData(
            generator_name=generator_name,
            approximation=synthetic_fragment,
            instruction=instruction,
        )
        reconstructor.state = ReconstructionState.create(list(reconstructor.generators.keys()))
        return reconstructor, generator_name, approximation_data

    def test_without_final_regeneration_stores_precomputed_audio_scaled_by_drive(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
    ) -> None:
        reconstructor, generator_name, approximation_data = self._setup(
            config,
            library_data,
            synthetic_fragment,
            final_regeneration=False,
        )
        reconstructor.update_state(approximation_data)
        expected = np.asarray(synthetic_fragment.audio) * reconstructor.config.generation.drive
        np.testing.assert_array_almost_equal(
            reconstructor.state.approximations[generator_name][0],
            expected,
        )

    def test_without_final_regeneration_does_not_run_generator(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
    ) -> None:
        reconstructor, generator_name, approximation_data = self._setup(
            config,
            library_data,
            synthetic_fragment,
            final_regeneration=False,
        )
        reconstructor.update_state(approximation_data)
        assert reconstructor.generators[generator_name].previous_instruction is None

    def test_with_final_regeneration_reruns_generator(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
    ) -> None:
        reconstructor, generator_name, approximation_data = self._setup(
            config,
            library_data,
            synthetic_fragment,
            final_regeneration=True,
        )
        reconstructor.update_state(approximation_data)
        assert reconstructor.generators[generator_name].previous_instruction is approximation_data.instruction


class TestReconstructorReconstruct:
    def test_state_is_populated_for_each_fragment(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        fragmented_audio: FragmentedAudio,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        reconstructor.state = ReconstructionState.create(list(reconstructor.generators.keys()))
        reconstructor.reconstruct(fragmented_audio)
        fragment_count = len(fragmented_audio.fragments_ids)
        for generator_name in reconstructor.generators:
            assert len(reconstructor.state.instructions[generator_name]) == fragment_count
            assert len(reconstructor.state.approximations[generator_name]) == fragment_count

    def test_approximations_have_correct_frame_length(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        fragmented_audio: FragmentedAudio,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        reconstructor.state = ReconstructionState.create(list(reconstructor.generators.keys()))
        reconstructor.reconstruct(fragmented_audio)
        for generator_name in reconstructor.generators:
            for approximation in reconstructor.state.approximations[generator_name]:
                assert len(approximation) == config.library.frame_length


class TestReconstructorCall:
    def test_non_path_argument_raises_type_error(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        with pytest.raises(TypeError):
            reconstructor(42)  # type: ignore[arg-type]

    def test_returns_reconstruction_for_valid_audio_path(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> None:
        from sampletones_core.audio import write_wave
        from sampletones_core.reconstructions.reconstruction.reconstruction import Reconstruction

        audio_path = tmp_path / "test.wav"
        audio = np.tile(synthetic_fragment.audio, 3).astype(np.float32)
        write_wave(audio_path, config.library.sample_rate, audio)
        reconstructor = _make_reconstructor(config, library_data)
        result = reconstructor(audio_path)
        assert isinstance(result, Reconstruction)
