from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import MIXER_LEVELS
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.reconstructor import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
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
        expected_names = set(config.generation.channels)
        assert set(reconstructor.channels.keys()) == expected_names

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
        coefficient = reconstructor.get_coefficient(audio, _full_setup(config))
        assert coefficient == pytest.approx(0.5 / _total_mixer(reconstructor))

    def test_coefficient_is_robust_to_a_lone_transient(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        frame_length = config.library.frame_length
        total_mixer = _total_mixer(reconstructor)
        audio = np.full(frame_length * 24, 0.05, dtype=np.float32)
        audio[:frame_length] = 1.0
        coefficient = reconstructor.get_coefficient(audio, _full_setup(config))
        assert coefficient == pytest.approx(0.05 / total_mixer, rel=1e-3)
        assert coefficient < 1.0 / total_mixer

    def test_louder_audio_produces_larger_coefficient(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        setup = _full_setup(config)
        quiet = np.ones(config.library.frame_length, dtype=np.float32) * 0.1
        loud = np.ones(config.library.frame_length, dtype=np.float32) * 0.9
        assert reconstructor.get_coefficient(loud, setup) > reconstructor.get_coefficient(quiet, setup)

    def test_a_capped_setup_anchors_to_what_one_frame_reaches(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        """One channel per frame reaches one channel's weight, so that is what the level is measured against."""
        reconstructor = _make_reconstructor(config, library_data)
        capped = StemsConfig.single_entry(list(config.generation.channels), channel_cap=1)
        audio = np.ones(config.library.frame_length, dtype=np.float32) * 0.5

        loudest = max(MIXER_LEVELS[generator.class_name()] for generator in reconstructor.channels.values())

        assert reconstructor.get_coefficient(audio, capped) == pytest.approx(0.5 / loudest)


def _full_setup(config: Config) -> StemsConfig:
    return StemsConfig.single_entry(list(config.generation.channels))


def _total_mixer(reconstructor: Reconstructor) -> float:
    return sum(MIXER_LEVELS[generator.class_name()] for generator in reconstructor.channels.values())


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


class TestReconstructorResetChannels:
    def test_reset_clears_generator_states(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        from sampletones_core.generators.implementation.noise import NoiseGenerator
        from sampletones_core.generators.implementation.pulse import PulseGenerator
        from sampletones_core.generators.implementation.triangle import (
            TriangleGenerator,
        )
        from sampletones_core.instructions import (
            NoiseInstruction,
            PulseInstruction,
            TriangleInstruction,
        )

        reconstructor = _make_reconstructor(config, library_data)
        for generator in reconstructor.channels.values():
            if isinstance(generator, PulseGenerator):
                generator.save_state(True, PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0))
            elif isinstance(generator, TriangleGenerator):
                generator.save_state(True, TriangleInstruction(on=True, pitch=60))
            elif isinstance(generator, NoiseGenerator):
                generator.save_state(True, NoiseInstruction(on=True, period=0, volume=10, short=False))

        assert all(gen.previous_instruction is not None for gen in reconstructor.channels.values())
        reconstructor.reset_generators()
        assert all(gen.previous_instruction is None for gen in reconstructor.channels.values())


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
        from sampletones_core.reconstructions.reconstruction.reconstruction import (
            Reconstruction,
        )

        audio_path = tmp_path / "test.wav"
        audio = np.tile(synthetic_fragment.audio, 3).astype(np.float32)
        write_wave(audio_path, config.library.sample_rate, audio)
        reconstructor = _make_reconstructor(config, library_data)
        result = reconstructor(audio_path)
        assert isinstance(result, Reconstruction)


class TestReconstructorFinalRegeneration:
    """What a frame records: the instruction rendered afresh, or the audio it was matched on."""

    def _tone_path(self, tmp_path: Path, config: Config, synthetic_fragment: Fragment) -> Path:
        from sampletones_core.audio import write_wave

        audio_path = tmp_path / "tone.wav"
        write_wave(audio_path, config.library.sample_rate, np.tile(synthetic_fragment.audio, 3).astype(np.float32))
        return audio_path

    def _reconstructor(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        final_regeneration: bool,
    ) -> Reconstructor:
        updated_config = config.model_copy(
            update={"generation": config.generation.model_copy(update={"final_regeneration": final_regeneration})}
        )
        return _make_reconstructor(updated_config, library_data)

    def test_final_regeneration_reruns_every_channel_generator(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> None:
        reconstructor = self._reconstructor(config, library_data, final_regeneration=True)

        reconstruction = reconstructor(self._tone_path(tmp_path, config, synthetic_fragment))

        assert reconstruction is not None
        for channel_name in reconstruction.playing_channels:
            generator = reconstructor.channels[channel_name]
            assert generator.previous_instruction is reconstruction.instructions[channel_name][-1]

    def test_without_final_regeneration_the_matched_audio_stands(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> None:
        reconstructor = self._reconstructor(config, library_data, final_regeneration=False)

        reconstruction = reconstructor(self._tone_path(tmp_path, config, synthetic_fragment))

        assert reconstruction is not None
        assert all(generator.previous_instruction is None for generator in reconstructor.channels.values())
