from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Final, List, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.algorithm import MAX_DRIVE, UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.matching import RowsRequest, ScoredCandidate, column_of
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy, xp
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.fragments import amplified

WORKER_SIGNAL_LENGTH: Final[int] = 1 << 20
DRIVE: Final[float] = 2.0
AVERAGED_SHIFTS: Final[int] = 400
AVERAGE_TOLERANCE: Final[float] = 0.05
SOUNDING_COST: Final[float] = 0.2
SILENT_COST: Final[float] = 0.5
LADDER_PITCH: Final[int] = 60
LADDER_DUTY_CYCLE: Final[int] = 0
LADDER_STEP: Final[int] = 2
QUIET_RUNG: Final[int] = 3
MIDDLE_RUNG: Final[int] = 7
REQUESTED_ROWS: Final[int] = 4
CHANNEL_PRICE: Final[float] = 0.01
UNPRICED: Final[float] = 0.0
SINGLE_SHORTLIST: Final[int] = 1
MUTE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=LADDER_PITCH, volume=0, duty_cycle=LADDER_DUTY_CYCLE)


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
        layer_data=(),
        signal_length=WORKER_SIGNAL_LENGTH,
    )


def _kinds(worker: ReconstructorWorker) -> List[GeneratorUnion]:
    """One generator per kind the run hands out, the lowest channel of each standing for it."""
    kinds: Dict[GeneratorClassName, GeneratorUnion] = {}
    for generator in worker.channels.values():
        kinds.setdefault(generator.class_name(), generator)

    return list(kinds.values())


def _generator_of(worker: ReconstructorWorker, instruction: InstructionUnion) -> GeneratorUnion:
    """The generator of the kind the instruction belongs to."""
    return next(generator for generator in _kinds(worker) if generator.get_instruction_type() is type(instruction))


def _rebuilt(worker: ReconstructorWorker, generation: GenerationConfig) -> ReconstructorWorker:
    """``worker`` built again under ``generation``."""
    return ReconstructorWorker(
        config=worker.config.model_copy(update={"generation": generation}),
        window=worker.window,
        channels=worker.channels,
        library_data=worker.library_data,
        layer_data=(),
        signal_length=WORKER_SIGNAL_LENGTH,
    )


def _shortlisting(worker: ReconstructorWorker, top_k: int) -> ReconstructorWorker:
    """``worker`` with a shortlist ``top_k`` long."""
    generation = worker.config.generation
    decoder = generation.decoder.model_copy(update={"top_k": top_k})
    return _rebuilt(worker, generation.model_copy(update={"decoder": decoder}))


def _priced(worker: ReconstructorWorker, channel_price: float) -> ReconstructorWorker:
    """``worker`` charging ``channel_price`` for each channel a frame sounds."""
    generation = worker.config.generation
    weights = generation.weights.model_copy(update={"channel_price": channel_price})
    return _rebuilt(worker, generation.model_copy(update={"weights": weights}))


def _instructions(worker: ReconstructorWorker, generator: GeneratorUnion) -> Tuple[InstructionUnion, ...]:
    return worker.matcher.candidate_provider.candidates({generator.class_name(): generator}).instructions


def _sounding(worker: ReconstructorWorker, target: Fragment, instruction: InstructionUnion) -> Contribution:
    """What ``instruction`` adds to ``target``, phased against it."""
    residual = np.asarray(target.audio, dtype=np.float64)
    power = worker.candidate_provider.power_of(instruction)
    return worker.matcher.contribution(instruction, residual, power, drive=UNIT_DRIVE)


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
        for generator in _kinds(worker):
            column = worker.matcher.score_column(
                synthetic_fragment,
                generator,
                FrameMix.empty(synthetic_fragment),
                drive=UNIT_DRIVE,
            )

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
            drive=UNIT_DRIVE,
        )

        assert column[0].instruction == audible_instruction
        assert column[0].cost == pytest.approx(0.0, abs=1e-3)

    def test_a_driven_candidate_answers_a_target_it_sounds_louder_than(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        extractor: FeatureExtractor,
        config: Config,
        window: Window,
    ) -> None:
        """A candidate scored at a drive answers the target its library sample sounds that loud over."""
        library_fragment = library_data[audible_instruction].get_fragment(0, config, window)
        target = amplified(extractor, library_fragment, UNIT_DRIVE / DRIVE)

        column = worker.matcher.score_column(
            target,
            _generator_of(worker, audible_instruction),
            FrameMix.empty(target),
            drive=DRIVE,
        )

        assert column[0].instruction == audible_instruction
        assert column[0].cost == pytest.approx(0.0, abs=1e-3)

    def test_silence_costs_what_the_mix_alone_costs(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        mix = FrameMix.empty(synthetic_fragment)
        generator = _kinds(worker)[0]

        column = worker.matcher.score_column(synthetic_fragment, generator, mix, drive=UNIT_DRIVE)

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
        covering = worker.matcher.score_column(target, generator, FrameMix.empty(target), drive=UNIT_DRIVE)[0]

        column = worker.matcher.score_column(
            target,
            generator,
            FrameMix.of(target, [covering.contribution]),
            drive=UNIT_DRIVE,
        )

        assert not column[0].instruction.on

    def test_a_priced_column_charges_each_sounding_candidate_the_price_and_its_silence_nothing(
        self,
        worker: ReconstructorWorker,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        library_data: InstructionLibraryData,
        synthetic_fragment: Fragment,
    ) -> None:
        weights = config.generation.weights.model_copy(update={"channel_price": CHANNEL_PRICE})
        priced = ReconstructorWorker(
            config=config.model_copy(update={"generation": config.generation.model_copy(update={"weights": weights})}),
            window=window,
            channels=channels,
            library_data=library_data,
            layer_data=(),
            signal_length=WORKER_SIGNAL_LENGTH,
        )
        for generator in _kinds(worker):
            plain = worker.matcher.score_column(
                synthetic_fragment, generator, FrameMix.empty(synthetic_fragment), drive=UNIT_DRIVE
            )
            charged = priced.matcher.score_column(
                synthetic_fragment, generator, FrameMix.empty(synthetic_fragment), drive=UNIT_DRIVE
            )

            costs = {candidate.instruction: candidate.cost for candidate in plain}
            assert {candidate.instruction for candidate in charged} == set(costs)
            for candidate in charged:
                assert candidate.cost == pytest.approx(
                    costs[candidate.instruction] + CHANNEL_PRICE * candidate.instruction.on
                )

    def test_a_shortlist_reaching_past_the_class_holds_every_candidate_once(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        """The silence joins the shortlist only where the spectral ranking left it out."""
        generator = _kinds(worker)[0]
        covering = _shortlisting(worker, len(_instructions(worker, generator)) + 1)

        column = covering.matcher.score_column(
            synthetic_fragment, generator, FrameMix.empty(synthetic_fragment), drive=UNIT_DRIVE
        )

        assert Counter(candidate.instruction for candidate in column) == Counter(_instructions(worker, generator))

    def test_a_shortlist_of_one_holds_the_best_row_and_the_silence(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        target = library_data[audible_instruction].get_fragment(0, config, window)
        single = _shortlisting(worker, SINGLE_SHORTLIST)

        column = single.matcher.score_column(
            target, _generator_of(worker, audible_instruction), FrameMix.empty(target), drive=UNIT_DRIVE
        )

        assert [candidate.instruction for candidate in column] == [
            audible_instruction,
            type(audible_instruction).null_instruction(),
        ]

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
            layer_data=(),
            signal_length=WORKER_SIGNAL_LENGTH,
        )

        with pytest.raises(ValueError, match="lacks the silent instruction"):
            worker.matcher.score_column(
                synthetic_fragment,
                pulse,
                FrameMix.empty(synthetic_fragment),
                drive=UNIT_DRIVE,
            )


class TestScoringTogether:
    """Several channels' rows, or several mixes, scored in one pass cost what each costs scored alone."""

    def _requests(self, worker: ReconstructorWorker, target: Fragment) -> List[RowsRequest]:
        first, second = _kinds(worker)[:2]
        held = worker.matcher.score_column(target, first, FrameMix.empty(target), drive=UNIT_DRIVE)[0]
        return [
            RowsRequest(
                generator=first,
                mix=FrameMix.empty(target),
                rows=self._rows(worker, first),
                powers=self._powers(worker, first, UNIT_DRIVE),
                drive=UNIT_DRIVE,
            ),
            RowsRequest(
                generator=second,
                mix=FrameMix.of(target, [held.contribution]),
                rows=self._rows(worker, second),
                powers=self._powers(worker, second, DRIVE),
                drive=DRIVE,
            ),
        ]

    @classmethod
    def _powers(cls, worker: ReconstructorWorker, generator: GeneratorUnion, drive: float) -> np.ndarray:
        """The library powers of ``_rows``, read at ``drive``."""
        candidates = worker.matcher.candidate_provider.candidates({generator.class_name(): generator})
        powers = np.asarray(to_numpy(candidates.powers), dtype=np.float64)
        return np.asarray(powers[list(cls._rows(worker, generator))] / drive**2)

    @staticmethod
    def _rows(worker: ReconstructorWorker, generator: GeneratorUnion) -> Tuple[int, ...]:
        """The first few candidates of the generator's class, as many as it holds up to ``REQUESTED_ROWS``."""
        held = len(worker.matcher.candidate_provider.candidates({generator.class_name(): generator}).instructions)
        return tuple(range(min(REQUESTED_ROWS, held)))

    def test_rows_scored_together_cost_what_each_channel_s_rows_cost_alone(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        requests = self._requests(worker, synthetic_fragment)

        together = worker.matcher.score_requests(synthetic_fragment, requests)

        for request, column in zip(requests, together):
            alone = worker.matcher.score_rows(
                synthetic_fragment, request.generator, request.mix, request.rows, drive=request.drive
            )
            assert [candidate.instruction for candidate in column] == [candidate.instruction for candidate in alone]
            assert [candidate.cost for candidate in column] == pytest.approx([candidate.cost for candidate in alone])

    def test_rows_a_column_shortlisted_cost_what_the_column_gives_them_beside_the_same_mix(
        self,
        worker: ReconstructorWorker,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        mix = FrameMix.of(synthetic_fragment, [_sounding(worker, synthetic_fragment, audible_instruction)])
        generator = _kinds(worker)[-1]
        column = worker.matcher.score_column(synthetic_fragment, generator, mix, drive=DRIVE)
        rows = [_instructions(worker, generator).index(candidate.instruction) for candidate in column]

        again = worker.matcher.score_rows(synthetic_fragment, generator, mix, rows, drive=DRIVE)

        assert [candidate.instruction for candidate in again] == [candidate.instruction for candidate in column]
        assert [candidate.cost for candidate in again] == pytest.approx([candidate.cost for candidate in column])

    def test_mixes_scored_together_cost_what_each_costs_alone(
        self,
        worker: ReconstructorWorker,
        synthetic_fragment: Fragment,
    ) -> None:
        mixes = [request.mix for request in self._requests(worker, synthetic_fragment)]

        together = worker.matcher.mix_costs(synthetic_fragment, mixes)

        assert list(together) == pytest.approx([worker.matcher.mix_cost(synthetic_fragment, mix) for mix in mixes])


class TestTheSpectralCostOfMixes:
    """The spectral cost of the frame with each row of a stack sounding, the first stage of every cost."""

    def test_a_stack_of_mixes_costs_what_each_mix_costs_alone(
        self,
        worker: ReconstructorWorker,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        power = worker.candidate_provider.power_of(audible_instruction)
        powers = np.stack([power, np.zeros_like(power), 2.0 * power])

        together = worker.matcher.spectral_costs(synthetic_fragment, powers)

        alone = [float(worker.matcher.spectral_costs(synthetic_fragment, row[None, :])[0]) for row in powers]
        assert list(together) == pytest.approx(alone)

    def test_the_frame_s_own_sound_costs_nothing_and_its_silence_costs_more(
        self,
        worker: ReconstructorWorker,
        library_data: InstructionLibraryData,
        audible_instruction: InstructionUnion,
        config: Config,
        window: Window,
    ) -> None:
        target = library_data[audible_instruction].get_fragment(0, config, window)
        power = worker.candidate_provider.power_of(audible_instruction)

        own, silent = worker.matcher.spectral_costs(target, np.stack([power, np.zeros_like(power)]))

        assert own == pytest.approx(0.0, abs=1e-5)
        assert silent > own

    def test_a_mix_alone_pays_the_price_of_each_channel_it_sounds(
        self,
        worker: ReconstructorWorker,
        audible_instruction: InstructionUnion,
        synthetic_fragment: Fragment,
    ) -> None:
        sounding = _sounding(worker, synthetic_fragment, audible_instruction)
        mixes = [FrameMix.of(synthetic_fragment, [sounding] * count) for count in range(3)]
        priced = _priced(worker, CHANNEL_PRICE)
        unpriced = _priced(worker, UNPRICED)

        charged = priced.matcher.mix_costs(synthetic_fragment, mixes) - unpriced.matcher.mix_costs(
            synthetic_fragment, mixes
        )

        assert list(charged) == pytest.approx([0.0, CHANNEL_PRICE, 2 * CHANNEL_PRICE])


@pytest.fixture(name="mute_worker", scope="module")
def mute_worker_fixture(
    config: Config,
    window: Window,
    extractor: FeatureExtractor,
    channels: Dict[ChannelName, GeneratorUnion],
) -> ReconstructorWorker:
    """A pulse sounding at volume zero beside its silence, which every frame scores alike, at no price."""
    generator = channels[ChannelName.PULSE1]
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in (generator.get_instruction_type().null_instruction(), MUTE)
    }
    weights = config.generation.weights.model_copy(update={"channel_price": UNPRICED})
    return ReconstructorWorker(
        config=config.model_copy(update={"generation": config.generation.model_copy(update={"weights": weights})}),
        window=window,
        channels={ChannelName.PULSE1: generator},
        library_data=InstructionLibraryData.create(config, data),
        layer_data=(),
        signal_length=WORKER_SIGNAL_LENGTH,
    )


class TestATieInAColumn:
    """A column lists the channel's silence ahead of a sounding row costing the same, in whichever order they came."""

    @pytest.mark.parametrize("muted_first", [True, False], ids=["the_mute_given_first", "the_silence_given_first"])
    def test_the_silence_stands_ahead_of_a_row_costing_the_same(
        self, mute_worker: ReconstructorWorker, synthetic_fragment: Fragment, muted_first: bool
    ) -> None:
        generator = mute_worker.channels[ChannelName.PULSE1]
        instructions = _instructions(mute_worker, generator)
        rows = [instructions.index(MUTE), instructions.index(generator.get_instruction_type().null_instruction())]

        column = mute_worker.matcher.score_rows(
            synthetic_fragment,
            generator,
            FrameMix.empty(synthetic_fragment),
            rows if muted_first else rows[::-1],
            drive=UNIT_DRIVE,
        )

        assert column[0].cost == column[1].cost
        assert [candidate.instruction.on for candidate in column] == [False, True]


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
        shifts = range(0, library_fragment.length, library_fragment.length // AVERAGED_SHIFTS)
        averaged = np.mean(
            [
                float(
                    to_numpy(
                        criterion.temporal_loss(
                            xp.asarray(synthetic_fragment.audio),
                            xp.asarray(library_fragment.get_fragment(shift, config, window).audio / DRIVE),
                        )
                    )[0]
                )
                for shift in shifts
            ]
        )

        contribution = worker.matcher.contribution(
            noise,
            np.asarray(synthetic_fragment.audio, dtype=np.float64),
            worker.candidate_provider.power_of(noise) / DRIVE**2,
            drive=DRIVE,
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

        searched = searching.matcher.contribution(audible_instruction, residual, power, drive=UNIT_DRIVE)
        kept = keeping.matcher.contribution(audible_instruction, residual, power, drive=UNIT_DRIVE)

        assert _temporal_loss(searching, synthetic_fragment, searched) <= _temporal_loss(
            keeping, synthetic_fragment, kept
        )


def _ladder_instructions(generator: GeneratorUnion) -> List[InstructionUnion]:
    """One pulse pitch at every other volume it holds, with the channel's silence beside them.

    Stepping over the volumes keeps the whole ladder inside the spectral shortlist, so the
    loudest rung stands before the full cost whatever drive the column is scored at.
    """
    rungs = sorted(
        (
            instruction
            for instruction in generator.get_possible_instructions()
            if instruction.on and instruction.pitch == LADDER_PITCH and instruction.duty_cycle == LADDER_DUTY_CYCLE
        ),
        key=lambda instruction: instruction.volume,
    )
    return [*rungs[::LADDER_STEP], generator.get_instruction_type().null_instruction()]


def _ladder_target(
    worker: ReconstructorWorker,
    config: Config,
    window: Window,
    volume: int,
) -> Fragment:
    """The frame the rung at ``volume`` sounds, which a drive is measured against."""
    rung = next(
        instruction for instruction in worker.library_data.keys() if instruction.on and instruction.volume == volume
    )
    return worker.library_data[rung].get_fragment(0, config, window)


def _winner(worker: ReconstructorWorker, target: Fragment, drive: float) -> InstructionUnion:
    """The row a channel plays in ``target`` at ``drive``."""
    generator = worker.channels[ChannelName.PULSE1]
    column = worker.matcher.score_column(target, generator, FrameMix.empty(target), drive=drive)
    return column[0].instruction


def _loudest(worker: ReconstructorWorker) -> InstructionUnion:
    """The loudest row the ladder holds, which is the level the channel saturates at."""
    return max(
        (instruction for instruction in worker.library_data.keys() if instruction.on),
        key=lambda instruction: instruction.volume,
    )


@pytest.fixture(scope="module")
def ladder_worker(
    config: Config,
    window: Window,
    extractor: FeatureExtractor,
    channels: Dict[ChannelName, GeneratorUnion],
) -> ReconstructorWorker:
    """A run over one pulse pitch at a ladder of volumes, which is what a drive climbs."""
    generator = channels[ChannelName.PULSE1]
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in _ladder_instructions(generator)
    }
    return ReconstructorWorker(
        config=config,
        window=window,
        channels={ChannelName.PULSE1: generator},
        library_data=InstructionLibraryData.create(config, data),
        layer_data=(),
        signal_length=WORKER_SIGNAL_LENGTH,
    )


class TestTheRowADriveReachesFor:
    """A drive lifts what a channel reaches for, up to the loudest row the channel holds."""

    def test_a_driven_channel_reaches_for_a_louder_row(
        self,
        ladder_worker: ReconstructorWorker,
        config: Config,
        window: Window,
    ) -> None:
        target = _ladder_target(ladder_worker, config, window, QUIET_RUNG)

        standing = _winner(ladder_worker, target, UNIT_DRIVE)
        driven = _winner(ladder_worker, target, DRIVE)

        assert standing.volume < driven.volume < _loudest(ladder_worker).volume

    def test_a_drive_the_channel_cannot_reach_settles_on_its_loudest_row(
        self,
        ladder_worker: ReconstructorWorker,
        config: Config,
        window: Window,
    ) -> None:
        target = _ladder_target(ladder_worker, config, window, MIDDLE_RUNG)

        assert _winner(ladder_worker, target, MAX_DRIVE) == _loudest(ladder_worker)


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
