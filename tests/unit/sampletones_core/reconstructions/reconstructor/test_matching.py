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
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy, xp
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20
AVERAGED_SHIFTS: Final[int] = 400
AVERAGE_TOLERANCE: Final[float] = 0.05


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
    A candidate playback lines up with the target is measured at its best phase, and a candidate whose
    frames show different stretches of a sequence by what it averages to over the phases it starts on,
    whether or not the matching searches for the best phase.
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
    def test_long_noise_costs_what_it_averages_to_over_its_shifts(
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
        library_fragment = library_data[noise]
        criterion = worker.scorer.criterion
        drive = config.generation.drive
        shifts = range(0, library_fragment.length, library_fragment.length // AVERAGED_SHIFTS)
        averaged = np.mean(
            [
                float(
                    to_numpy(
                        criterion.temporal_loss(
                            xp.asarray(synthetic_fragment.audio),
                            xp.asarray(library_fragment.get_fragment(shift, config, window).audio * drive),
                        )
                    )[0]
                )
                for shift in shifts
            ]
        )

        approximation = worker.matcher.build_approximation(synthetic_fragment, noise, channels[ChannelName.NOISE])
        cost = float(to_numpy(approximation.temporal_loss(synthetic_fragment, criterion))[0])

        assert cost == pytest.approx(averaged, rel=AVERAGE_TOLERANCE)

    def test_a_note_searched_for_costs_no_more_than_at_its_library_phase(
        self,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        searching = _searching(config, window, channels, library_data, True)
        keeping = _searching(config, window, channels, library_data, False)
        generator = get_generator_by_instruction(
            audible_instruction,
            get_remaining_generator_classes(dict(channels)),
        )
        criterion = searching.scorer.criterion

        searched = searching.matcher.build_approximation(synthetic_fragment, audible_instruction, generator)
        kept = keeping.matcher.build_approximation(synthetic_fragment, audible_instruction, generator)

        assert float(to_numpy(searched.temporal_loss(synthetic_fragment, criterion))[0]) <= float(
            to_numpy(kept.temporal_loss(synthetic_fragment, criterion))[0]
        )
