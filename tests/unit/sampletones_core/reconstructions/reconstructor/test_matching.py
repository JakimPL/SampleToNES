from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
    get_remaining_generator_classes,
)
from sampletones_core.instructions import InstructionUnion, NoiseInstruction
from sampletones_core.library import InstructionLibraryData
from sampletones_core.reconstructions.reconstructor.approximation import (
    ExpectedApproximation,
    WaveformApproximation,
)
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20
TONE_CYCLES_PER_FRAME: Final[int] = 3
TONE_AMPLITUDE: Final[float] = 0.015
TONE_FRAMES: Final[int] = 8
TONE_FRAME: Final[int] = 4


def _long_noise(library_data: InstructionLibraryData) -> NoiseInstruction:
    return next(
        instruction
        for instruction in library_data.keys()
        if isinstance(instruction, NoiseInstruction) and instruction.on and not instruction.short
    )


def _searching(
    config: Config,
    window: Window,
    channels: Dict[ChannelName, GeneratorUnion],
    library_data: InstructionLibraryData,
    find_best_phase: bool,
) -> ReconstructorWorker:
    calculation = config.generation.calculation.model_copy(update={"find_best_phase": find_best_phase})
    searching = config.model_copy(
        update={"generation": config.generation.model_copy(update={"calculation": calculation})}
    )
    return ReconstructorWorker(
        config=searching,
        window=window,
        channels=channels,
        library_data=library_data,
        signal_length=WORKER_SIGNAL_LENGTH,
    )


class TestTwoStageScoring:
    def test_shortlist_is_ranked_by_candidate_cost_best_first(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        remaining_generator_classes = get_remaining_generator_classes(dict(worker.channels))
        scored = worker.matcher.score_candidates(synthetic_fragment, remaining_generator_classes)

        assert 0 < len(scored) <= worker.matcher.top_k
        costs = [candidate.cost for candidate in scored]
        assert costs == sorted(costs)

    def test_phase_shifted_target_selects_its_source_instruction_at_near_zero_cost(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        """
        A target that is a phase-shifted rendering of a library instruction wins with
        a near-zero cost: the spectral shortlist is phase-independent, and the
        temporal term is evaluated on the candidate aligned to the target, so the
        phase accident carries no penalty.
        """
        instruction = audible_instruction
        library_fragment = library_data[instruction]
        shifted_target = library_fragment.get_fragment(library_fragment.length // 4, config, window)

        remaining_generator_classes = get_remaining_generator_classes(dict(worker.channels))
        scored = worker.matcher.score_candidates(shifted_target, remaining_generator_classes)

        assert scored[0].instruction == instruction
        assert scored[0].cost == pytest.approx(0.0, abs=1e-3)


class TestClassRestrictedShortlist:
    def test_one_class_keeps_the_candidate_a_wider_scoring_picked(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        """Scoring one generator class alone reaches the winner the wider scoring picked.

        The shortlist is drawn by spectral rank, so a candidate that outranked every other
        class's candidates outranks its own class's rejects too. That is what lets a frame's
        ownership be settled across classes while the column the decoder reads holds the
        winning channel's own alternatives.
        """
        wide_classes = get_remaining_generator_classes(dict(worker.channels))
        winner = worker.matcher.score_candidates(synthetic_fragment, wide_classes)[0]
        generator = get_generator_by_instruction(winner.instruction, wide_classes)

        column = worker.matcher.score_candidates(
            synthetic_fragment,
            {generator.class_name(): generator},
        )

        assert winner.instruction in [candidate.instruction for candidate in column]


class TestHowACandidateIsMeasured(BaseTestSuite):
    """
    A candidate whose frames repeat one shape is measured by its waveform, and a candidate whose
    frames show different stretches of a sequence by its expected contribution, whether or not the
    matching searches for the best phase.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        find_best_phase: bool

    test_cases = (
        TestCase(label="searching_the_phase", find_best_phase=True),
        TestCase(label="keeping_the_carried_phase", find_best_phase=False),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_long_noise_is_measured_by_its_expectation(
        self,
        test_case: TestCase,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
    ) -> None:
        worker = _searching(config, window, channels, library_data, test_case.find_best_phase)
        noise = _long_noise(library_data)

        approximation = worker.matcher.build_approximation(synthetic_fragment, noise, channels[ChannelName.NOISE])

        assert isinstance(approximation, ExpectedApproximation)
        np.testing.assert_array_equal(
            approximation.rendering.audio,
            worker.candidate_provider.get_approximation(noise, channels[ChannelName.NOISE]).audio,
        )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_note_is_measured_by_its_waveform(
        self,
        test_case: TestCase,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        worker = _searching(config, window, channels, library_data, test_case.find_best_phase)
        generator = get_generator_by_instruction(
            audible_instruction,
            get_remaining_generator_classes(dict(channels)),
        )

        approximation = worker.matcher.build_approximation(synthetic_fragment, audible_instruction, generator)

        rendered = (
            worker.phase_aligner.align(synthetic_fragment, audible_instruction)
            if test_case.find_best_phase
            else worker.candidate_provider.get_approximation(audible_instruction, generator)
        )
        assert isinstance(approximation, WaveformApproximation)
        np.testing.assert_array_equal(approximation.rendering.audio, rendered.audio)


class TestNoiseOverATone:
    def test_long_noise_on_a_zero_mean_tone_costs_at_least_silence(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        channels: Dict[ChannelName, GeneratorUnion],
        config: Config,
        extractor: FeatureExtractor,
    ) -> None:
        """
        Noise the channel renders from wherever its sequence stands carries nothing of a tone's
        shape, so over a tone whose frame averages to zero it adds its own spread to the difference
        and scores no closer than silence does.
        """
        frame_length = config.library.frame_length
        samples = np.arange(frame_length * TONE_FRAMES)
        audio = TONE_AMPLITUDE * np.sin(2 * np.pi * TONE_CYCLES_PER_FRAME * samples / frame_length)
        target = extractor.extract(audio.astype(np.float32))[TONE_FRAME]
        criterion = worker.scorer.criterion

        noise = worker.matcher.build_approximation(target, _long_noise(library_data), channels[ChannelName.NOISE])
        silence = WaveformApproximation(target * 0.0)

        assert float(noise.temporal_loss(target, criterion)[0]) >= float(silence.temporal_loss(target, criterion)[0])
