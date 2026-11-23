from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Mapping, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.audio import write_wave
from sampletones_core.configs import Config
from sampletones_core.configs.generation import AssignmentConfig, ChannelInertia
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    AssignmentMethod,
    ChannelName,
    GeneratorClassName,
    LevelMethod,
    SelectorName,
)
from sampletones_core.fft import Fragment, Window
from sampletones_core.generators import FULL_SCALE_RMS_LEVELS
from sampletones_core.generators.render import render_channels
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.progress import ReconstructionProgress
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels
from sampletones_core.reconstructions.reconstructor.decoder.base import Alternatives, Streams
from sampletones_core.reconstructions.reconstructor.decoder.viterbi import ViterbiDecoder
from sampletones_core.reconstructions.reconstructor.reconstructor import Reconstructor
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.stage import ReconstructionStage
from sampletones_shared.exceptions import NoLibraryDataError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.progress import RecordingReporter

from .conftest import rendered_audio

TRIANGLE_LEVEL: Final[float] = FULL_SCALE_RMS_LEVELS[GeneratorClassName.TRIANGLE_GENERATOR]
SINE_FRAMES: Final[int] = 30
SINE_AMPLITUDE: Final[float] = 0.8
SINE_CYCLES_PER_FRAME: Final[int] = 4
OFF_RATE: Final[int] = 48000
OFF_RATE_ABOVE: Final[int] = 96000
SQUARE_PEAK: Final[float] = 0.5
SQUARE_FREQUENCY: Final[float] = 220.0
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HELD_FRAMES: Final[int] = 32
LEVEL_TOLERANCE: Final[float] = 0.05
TRUE_LEVEL: Final[float] = 1.0
PASSED_FRAMES: Final[int] = 8
NO_INERTIA: Final[ChannelInertia] = ChannelInertia(pulse1=0.0, pulse2=0.0, triangle=0.0, noise=0.0)

Decode = Tuple[Alternatives, Streams]


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

    def test_a_relative_path_is_recorded_from_the_folder_it_was_given_in(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_wave(tmp_path / "tone.wav", config.library.sample_rate, np.tile(synthetic_fragment.audio, 3))
        monkeypatch.chdir(tmp_path)

        reconstruction = _make_reconstructor(config, library_data)(Path("tone.wav"))

        assert reconstruction is not None
        assert reconstruction.audio_filepath == (tmp_path / "tone.wav",)


class RecordingObserver:
    """Keeps what a run's observer hears, one hearing per stage."""

    def __init__(self) -> None:
        self.alternatives: List[Alternatives] = []
        self.streams: List[Streams] = []

    def assigned(self, alternatives: Alternatives) -> None:
        self.alternatives.append(alternatives)

    def decoded(self, streams: Streams) -> None:
        self.streams.append(streams)


class TestTheObserver:
    """An observer hears the columns a run offered and the streams it decoded, once each."""

    def _observed(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> RecordingObserver:
        audio_path = tmp_path / "tone.wav"
        write_wave(audio_path, config.library.sample_rate, np.tile(synthetic_fragment.audio, 3).astype(np.float32))
        observer = RecordingObserver()
        reconstruction = _make_reconstructor(config, library_data)(audio_path, observe=observer)
        assert reconstruction is not None
        return observer

    def test_every_channel_in_play_is_heard_with_a_column_and_a_decoded_candidate_per_frame(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> None:
        observer = self._observed(config, library_data, synthetic_fragment, tmp_path)

        (alternatives,), (streams,) = observer.alternatives, observer.streams
        lattices = alternatives.lattices
        assert set(lattices) == set(streams)
        for channel_name, lattice in lattices.items():
            assert len(lattice) == len(streams[channel_name])

    def test_each_decoded_candidate_is_one_its_frame_s_column_offered(
        self,
        config: Config,
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
        tmp_path: Path,
    ) -> None:
        observer = self._observed(config, library_data, synthetic_fragment, tmp_path)

        (alternatives,), (streams,) = observer.alternatives, observer.streams
        lattices = alternatives.lattices
        for channel_name, stream in streams.items():
            for column, candidate in zip(lattices[channel_name], stream):
                assert candidate.instruction in [offered.instruction for offered in column]


class TestDecodingWholeCombinations:
    """Under the combinations decoder every decoded frame is one whole combination its stem pooled."""

    def test_every_decoded_frame_is_a_combination_its_stem_pooled(
        self, tmp_path: Path, config: Config, joint_library: InstructionLibraryData
    ) -> None:
        generation = config.generation.model_copy(
            update={
                "assignment": AssignmentConfig(method=AssignmentMethod.JOINT),
                "decoder": config.generation.decoder.model_copy(update={"selector": SelectorName.COMBINATIONS}),
            }
        )
        combined = config.model_copy(update={"generation": generation})
        path = tmp_path / "chord.wav"
        audio = rendered_audio(combined, {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD}, HELD_FRAMES)
        write_wave(path, combined.library.sample_rate, audio.astype(np.float32))
        observer = RecordingObserver()

        reconstruction = _make_reconstructor(combined, joint_library)(path, observe=observer)

        assert reconstruction is not None
        (alternatives,), (streams,) = observer.alternatives, observer.streams
        assert alternatives.pools
        for stem_pools in alternatives.pools.values():
            for frame, pool in enumerate(stem_pools.frames):
                decoded = tuple(streams[name][frame].instruction for name in stem_pools.channel_names)
                offered = [tuple(candidate.instruction for candidate in combination.candidates) for combination in pool]
                assert decoded in offered


@pytest.fixture(name="decodes")
def decodes_fixture(monkeypatch: pytest.MonkeyPatch) -> List[Decode]:
    """Every decode the Viterbi decoder makes in the case: the alternatives it read and the streams it answered."""
    decodes: List[Decode] = []
    decode = ViterbiDecoder.decode

    def recorded(decoder: ViterbiDecoder, alternatives: Alternatives) -> Streams:
        streams = decode(decoder, alternatives)
        decodes.append((alternatives, streams))
        return streams

    monkeypatch.setattr(ViterbiDecoder, "decode", recorded)
    return decodes


class TestDecidingAmongNeighbors:
    """A run decodes its first assignment, then assigns and decodes again once per neighbor pass.

    The observer hears the last assignment and the streams decoded from it, which the run plays. The
    progress the run reports counts every pass within matching, so it only moves forward.
    """

    @staticmethod
    def _passing(config: Config, neighbors: int) -> Config:
        """``config`` assigning jointly through ``neighbors`` neighbor passes, decoded by the Viterbi decoder."""
        generation = config.generation.model_copy(
            update={
                "assignment": AssignmentConfig(method=AssignmentMethod.JOINT, neighbors=neighbors, inertia=NO_INERTIA),
                "decoder": config.generation.decoder.model_copy(update={"selector": SelectorName.VITERBI}),
            }
        )
        return config.model_copy(update={"generation": generation})

    @staticmethod
    def _chord(tmp_path: Path, config: Config) -> Path:
        """A held bass under a lead, written where ``tmp_path`` points."""
        path = tmp_path / "chord.wav"
        audio = rendered_audio(config, {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD}, PASSED_FRAMES)
        write_wave(path, config.library.sample_rate, audio.astype(np.float32))
        return path

    @pytest.mark.parametrize("neighbors", [0, 2], ids=["no_pass", "two_passes"])
    def test_each_pass_decodes_anew_and_the_last_decode_is_the_one_played(
        self,
        tmp_path: Path,
        config: Config,
        joint_library: InstructionLibraryData,
        decodes: List[Decode],
        neighbors: int,
    ) -> None:
        passing = self._passing(config, neighbors)
        observer = RecordingObserver()

        reconstruction = _make_reconstructor(passing, joint_library)(self._chord(tmp_path, passing), observe=observer)

        assert reconstruction is not None
        assert len(decodes) == 1 + neighbors
        read, answered = decodes[-1]
        (heard,), (decoded,) = observer.alternatives, observer.streams
        assert heard.lattices is read.lattices
        assert decoded is answered
        assert len({id(alternatives.lattices) for alternatives, _ in decodes}) == len(decodes)

    @pytest.mark.parametrize("neighbors", [0, 2], ids=["no_pass", "two_passes"])
    def test_the_progress_only_rises_and_matching_counts_the_frames_of_every_pass(
        self,
        tmp_path: Path,
        config: Config,
        joint_library: InstructionLibraryData,
        neighbors: int,
    ) -> None:
        passing = self._passing(config, neighbors)
        reconstructor = _make_reconstructor(passing, joint_library)
        stems_config = StemsConfig.single_entry(StemSettings.covering(list(reconstructor.channel_names)))
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter()

        reconstruction = reconstructor.reconstruct([self._chord(tmp_path, passing)], stems_config, report=reporter)

        assert reconstruction is not None
        fractions = [progress.fraction for progress in reporter.reports]
        frames = len(next(iter(reconstruction.instructions.values())))
        matching = [progress for progress in reporter.reports if progress.stage == ReconstructionStage.MATCHING]
        assert fractions == sorted(fractions)
        assert {progress.total for progress in matching} == {frames * (1 + neighbors)}
        assert matching[-1].completed == matching[-1].total


class TestTheAudioAReconstructionRecords:
    """A frame records its instruction rendered afresh, which is the audio the channel plays."""

    def _tone_path(self, tmp_path: Path, config: Config, synthetic_fragment: Fragment) -> Path:
        from sampletones_core.audio import write_wave

        audio_path = tmp_path / "tone.wav"
        write_wave(audio_path, config.library.sample_rate, np.tile(synthetic_fragment.audio, 3).astype(np.float32))
        return audio_path

    def test_every_channel_spans_the_frames_its_stream_describes(
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
            frames = len(reconstruction.instructions[channel_name])
            assert len(rendered_channels(reconstruction)[channel_name]) == frames * config.library.frame_length

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
                rendered_channels(reconstruction)[channel_name],
                rendered[channel_name],
                atol=1e-6,
            )


class TestARecordingIsReadAtTheLevelItsConversionMatches:
    """Calibration compares a reconstruction with the recording it was made from, so the recording
    is read at the level the conversion matched: scaled after it reaches the library's rate, as the
    conversion scales it. Resampling a square wave rings above its peak, which a scale taken before
    resampling would leave standing past full range."""

    @pytest.mark.parametrize("recording_rate", [OFF_RATE, OFF_RATE_ABOVE, Config().library.sample_rate])
    def test_the_recording_reaches_full_range_at_any_recording_rate(
        self,
        tmp_path: Path,
        config: Config,
        library_data: InstructionLibraryData,
        recording_rate: int,
    ) -> None:
        unquantized = config.model_copy(
            update={"general": config.general.model_copy(update={"normalize": True, "quantize": False})}
        )
        path = _write_square(tmp_path / "square.wav", recording_rate)
        reconstructor = _make_reconstructor(unquantized, library_data)

        loaded = reconstructor.load_audio([path])

        assert float(np.max(np.abs(loaded))) == pytest.approx(1.0, rel=1e-6)
        np.testing.assert_array_equal(loaded, reconstructor._load_stem_recordings([path]).recordings[0])

    def test_a_silent_recording_stays_silent(
        self, tmp_path: Path, config: Config, library_data: InstructionLibraryData
    ) -> None:
        path = tmp_path / "silence.wav"
        write_wave(path, OFF_RATE, np.zeros(OFF_RATE // 10, dtype=np.float32))

        loaded = _make_reconstructor(config, library_data).load_audio([path])

        assert not np.any(loaded)


class TestTheFittedWorkingLevel:
    """Under ``fitted`` a bass line on the triangle sets the working level, so the triangle plays it at its one level."""

    @staticmethod
    def _unnormalized(config: Config, level: LevelMethod) -> Config:
        return config.model_copy(
            update={"general": config.general.model_copy(update={"normalize": False, "level": level})}
        )

    @staticmethod
    def _bass_under_a_lead(tmp_path: Path, config: Config) -> Path:
        return TestTheFittedWorkingLevel._written(
            tmp_path / "bass.wav", config, {ChannelName.TRIANGLE: BASS, ChannelName.PULSE1: LEAD}
        )

    @staticmethod
    def _written(path: Path, config: Config, notes: Mapping[ChannelName, InstructionUnion]) -> Path:
        audio = rendered_audio(config, notes, HELD_FRAMES)
        write_wave(path, config.library.sample_rate, audio.astype(np.float32))
        return path

    def test_a_held_bass_brings_the_level_to_the_one_its_frames_were_played_at(
        self, tmp_path: Path, config: Config, joint_library: InstructionLibraryData
    ) -> None:
        fitted = self._unnormalized(config, LevelMethod.FITTED)

        reconstruction = _make_reconstructor(fitted, joint_library)(self._bass_under_a_lead(tmp_path, fitted))

        assert reconstruction is not None
        assert reconstruction.coefficient == pytest.approx(TRUE_LEVEL, rel=LEVEL_TOLERANCE)

    def test_the_coefficient_method_sets_the_level_by_the_frames_loudness(
        self, tmp_path: Path, config: Config, joint_library: InstructionLibraryData
    ) -> None:
        plain = self._unnormalized(config, LevelMethod.COEFFICIENT)

        reconstruction = _make_reconstructor(plain, joint_library)(self._bass_under_a_lead(tmp_path, plain))

        assert reconstruction is not None
        assert reconstruction.coefficient != pytest.approx(TRUE_LEVEL, rel=LEVEL_TOLERANCE)

    def test_a_recording_holding_no_triangle_line_keeps_the_coefficient_under_fitted(
        self, tmp_path: Path, config: Config, joint_library: InstructionLibraryData
    ) -> None:
        fitted = self._unnormalized(config, LevelMethod.FITTED)
        reconstructor = _make_reconstructor(fitted, joint_library)
        path = self._written(tmp_path / "lead.wav", fitted, {ChannelName.PULSE1: LEAD})

        reconstruction = reconstructor(path)

        assert reconstruction is not None
        assert reconstruction.coefficient == reconstructor.get_coefficient(
            reconstructor.load_audio([path]), _full_setup(fitted)
        )


def _write_square(path: Path, sample_rate: int) -> Path:
    time = np.arange(sample_rate // 4) / sample_rate
    square = SQUARE_PEAK * np.sign(np.sin(2 * np.pi * SQUARE_FREQUENCY * time))
    write_wave(path, sample_rate, square.astype(np.float32))
    return path
