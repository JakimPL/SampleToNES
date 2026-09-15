from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Final

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion, get_generator_by_instruction, get_remaining_generator_classes
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate, column_of
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy, xp
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20
AVERAGED_SHIFTS: Final[int] = 400
AVERAGE_TOLERANCE: Final[float] = 0.05
SOUNDING_COST: Final[float] = 0.2
SILENT_COST: Final[float] = 0.5


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


def _generator_of(worker: ReconstructorWorker, instruction: InstructionUnion) -> GeneratorUnion:
    return get_generator_by_instruction(instruction, get_remaining_generator_classes(dict(worker.channels)))


def _temporal_loss(worker: ReconstructorWorker, target: Fragment, contribution: Contribution) -> float:
    loss = worker.scorer.criterion.expected_temporal_loss(
        xp.asarray(target.audio, dtype=xp.float64),
        xp.asarray(contribution.expectation),
        contribution.variance,
    )
    return float(to_numpy(loss)[0])


class TestScoreColumn:
    def test_a_column_is_ranked_by_frame_cost_with_the_channel_s_silence_among_it(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        for generator in get_remaining_generator_classes(dict(worker.channels)).values():
            column = worker.matcher.score_column(synthetic_fragment, generator, FrameMix.empty(synthetic_fragment))

            costs = [candidate.cost for candidate in column]
            assert costs == sorted(costs)
            assert len(column) <= worker.matcher.top_k + 1
            assert any(not candidate.instruction.on for candidate in column)

    def test_a_phase_shifted_rendering_wins_its_class_at_near_zero_cost(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        """
        The spectral shortlist is phase-independent and the candidate's waveform is aligned to the
        target, so the phase accident carries no penalty.
        """
        library_fragment = library_data[audible_instruction]
        shifted_target = library_fragment.get_fragment(library_fragment.length // 4, config, window)

        column = worker.matcher.score_column(
            shifted_target,
            _generator_of(worker, audible_instruction),
            FrameMix.empty(shifted_target),
        )

        assert column[0].instruction == audible_instruction
        assert column[0].cost == pytest.approx(0.0, abs=1e-3)

    def test_silence_costs_what_the_mix_alone_costs(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        mix = FrameMix.empty(synthetic_fragment)
        generator = next(iter(get_remaining_generator_classes(dict(worker.channels)).values()))

        column = worker.matcher.score_column(synthetic_fragment, generator, mix)

        silence = next(candidate for candidate in column if not candidate.instruction.on)
        assert silence.cost == pytest.approx(worker.matcher.mix_cost(synthetic_fragment, mix), rel=1e-6)

    def test_a_sound_the_mix_already_holds_is_left_silent(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        """Adding what the frame already sounds costs more than silence, so the channel's head is its silence."""
        target = library_data[audible_instruction].get_fragment(0, config, window)
        generator = _generator_of(worker, audible_instruction)
        covering = worker.matcher.score_column(target, generator, FrameMix.empty(target))[0]

        column = worker.matcher.score_column(target, generator, FrameMix.of(target, [covering.contribution]))

        assert not column[0].instruction.on

    def test_a_library_without_the_class_s_silence_is_refused(
        self,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        extractor: FeatureExtractor,
        synthetic_fragment: Fragment,
    ) -> None:
        pulse = channels[ChannelName.PULSE1]
        data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
            instruction: InstructionLibraryFragment.create(pulse, instruction, extractor)
            for instruction in list(pulse.get_possible_instructions())[1:3]
        }
        worker = ReconstructorWorker(
            config=config,
            window=window,
            channels={ChannelName.PULSE1: pulse},
            library_data=InstructionLibraryData.create(config, data),
            signal_length=WORKER_SIGNAL_LENGTH,
        )

        with pytest.raises(ValueError, match="lacks the silent instruction"):
            worker.matcher.score_column(synthetic_fragment, pulse, FrameMix.empty(synthetic_fragment))


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

        contribution = worker.matcher.contribution(
            noise,
            np.asarray(synthetic_fragment.audio, dtype=np.float64),
            worker.candidate_provider.power_of(noise),
        )

        assert _temporal_loss(worker, synthetic_fragment, contribution) == pytest.approx(
            averaged, rel=AVERAGE_TOLERANCE
        )

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
        residual = np.asarray(synthetic_fragment.audio, dtype=np.float64)
        power = searching.candidate_provider.power_of(audible_instruction)

        searched = searching.matcher.contribution(audible_instruction, residual, power)
        kept = keeping.matcher.contribution(audible_instruction, residual, power)

        assert _temporal_loss(searching, synthetic_fragment, searched) <= _temporal_loss(
            keeping, synthetic_fragment, kept
        )


class TestColumnOf:
    def _column(self) -> tuple[ScoredCandidate, ...]:
        silence = Contribution.silence(1, 1)
        return (
            ScoredCandidate(PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=1), SOUNDING_COST, silence),
            ScoredCandidate(PulseInstruction(on=True, pitch=61, volume=8, duty_cycle=1), SOUNDING_COST, silence),
            ScoredCandidate(PulseInstruction.null_instruction(), SILENT_COST, silence),
        )

    def test_a_single_state_decoder_reads_the_head_alone(self) -> None:
        column = self._column()
        assert column_of(column, 1) == column[:1]

    def test_a_wider_column_keeps_the_channel_s_silence(self) -> None:
        column = self._column()
        assert column_of(column, 2) == (column[0], column[2])

    def test_a_column_already_holding_its_silence_keeps_its_order(self) -> None:
        column = self._column()
        assert column_of(column, 3) == column
