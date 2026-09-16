from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, List
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
    GeneratorClassName,
)
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import FULL_SCALE_RMS_LEVELS
from sampletones_core.generators.render import render_channels
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.reconstructor import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.exceptions import NoLibraryDataError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TRIANGLE_LEVEL: Final[float] = FULL_SCALE_RMS_LEVELS[GeneratorClassName.TRIANGLE_GENERATOR]
SINE_FRAMES: Final[int] = 30
SINE_AMPLITUDE: Final[float] = 0.8
SINE_CYCLES_PER_FRAME: Final[int] = 4


def _make_reconstructor(config: Config, library_data: InstructionLibraryData) -> Reconstructor:
    mock_library = MagicMock()
    mock_library.get.return_value = library_data
    mock_library.create_key.return_value = MagicMock()
    mock_library.get_path.return_value = "test/path"
    return Reconstructor(config, frozenset(DEFAULT_CHANNELS), library=mock_library)


class TestReconstructorInit:
    def test_generators_initialized_from_config(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        expected_names = set(DEFAULT_CHANNELS)
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
            Reconstructor(config, frozenset(DEFAULT_CHANNELS), library=mock_library)


class TestReconstructorGetCoefficient:
    def test_uniform_audio_anchors_to_its_level(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        audio = np.ones(config.library.frame_length, dtype=np.float32) * 0.5
        coefficient = reconstructor.get_coefficient(audio, _full_setup(config))
        assert coefficient == pytest.approx(0.5 / TRIANGLE_LEVEL)

    def test_coefficient_is_robust_to_a_lone_transient(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        frame_length = config.library.frame_length
        audio = np.full(frame_length * 24, 0.05, dtype=np.float32)
        audio[:frame_length] = 1.0
        coefficient = reconstructor.get_coefficient(audio, _full_setup(config))
        assert coefficient == pytest.approx(0.05 / TRIANGLE_LEVEL, rel=1e-3)
        assert coefficient < 1.0 / TRIANGLE_LEVEL

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

    def test_a_steady_sine_lands_at_the_level_a_full_volume_triangle_plays(
        self,
        config: Config,
        library_data: InstructionLibraryData,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        frame_length = config.library.frame_length
        phase = np.arange(frame_length * SINE_FRAMES) * SINE_CYCLES_PER_FRAME / frame_length
        sine = (SINE_AMPLITUDE * np.sin(2.0 * np.pi * phase)).astype(np.float32)

        scaled = sine / reconstructor.get_coefficient(sine, _full_setup(config))

        level = float(np.sqrt(np.mean(np.square(scaled.astype(np.float64)))))
        assert level == pytest.approx(TRIANGLE_LEVEL, rel=1e-2)


class TestReconstructorWorkingLevel(BaseTestSuite):
    """The working level is the full-scale RMS level of the quietest tone channel a setup covers."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channels: List[ChannelName]
        anchor: GeneratorClassName

    test_cases = (
        TestCase(
            label="triangle_among_the_tone_channels",
            channels=[ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE],
            anchor=GeneratorClassName.TRIANGLE_GENERATOR,
        ),
        TestCase(
            label="pulse_without_the_triangle",
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
            anchor=GeneratorClassName.PULSE_GENERATOR,
        ),
        TestCase(
            label="noise_without_a_tone_channel",
            channels=[ChannelName.NOISE],
            anchor=GeneratorClassName.NOISE_GENERATOR,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_level_follows_the_covered_channels(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        test_case: TestCase,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)
        setup = StemsConfig.single_entry(StemSettings.covering(test_case.channels))
        audio = np.ones(config.library.frame_length, dtype=np.float32) * 0.5

        assert reconstructor.get_coefficient(audio, setup) == pytest.approx(
            0.5 / FULL_SCALE_RMS_LEVELS[test_case.anchor]
        )


def _full_setup(config: Config) -> StemsConfig:
    return StemsConfig.single_entry(StemSettings.covering(list(DEFAULT_CHANNELS)))


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


class TestTheAudioAReconstructionRecords:
    """A frame records its instruction rendered afresh, which is the audio the channel plays."""

    def _tone_path(self, tmp_path: Path, config: Config, synthetic_fragment: Fragment) -> Path:
        from sampletones_core.audio import write_wave

        audio_path = tmp_path / "tone.wav"
        write_wave(audio_path, config.library.sample_rate, np.tile(synthetic_fragment.audio, 3).astype(np.float32))
        return audio_path

    def test_every_channel_generator_renders_the_frames_it_records(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> None:
        reconstructor = _make_reconstructor(config, library_data)

        reconstruction = reconstructor(self._tone_path(tmp_path, config, synthetic_fragment))

        assert reconstruction is not None
        for channel_name in reconstruction.playing_channels:
            generator = reconstructor.channels[channel_name]
            sounding = [instruction for instruction in reconstruction.instructions[channel_name] if instruction.on]
            assert generator.previous_instruction is sounding[-1]

    @pytest.mark.parametrize("reset_phase", [False, True], ids=["carried_phase", "reset_phase"])
    def test_the_recorded_audio_is_what_the_channels_render(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
        reset_phase: bool,
    ) -> None:
        """The phase a new note starts on follows the configuration in both, so an export plays what
        the reconstruction shows."""
        resetting = config.model_copy(
            update={"generation": config.generation.model_copy(update={"reset_phase": reset_phase})}
        )
        reconstructor = _make_reconstructor(resetting, library_data)

        reconstruction = reconstructor(self._tone_path(tmp_path, resetting, synthetic_fragment))

        assert reconstruction is not None
        rendered = render_channels(reconstruction.instructions, resetting)
        for channel_name in reconstruction.playing_channels:
            np.testing.assert_allclose(
                reconstruction.approximations[channel_name],
                rendered[channel_name] * resetting.generation.drive,
                atol=1e-6,
            )
