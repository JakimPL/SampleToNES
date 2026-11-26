from dataclasses import dataclass
from typing import Any, Dict, Final, FrozenSet, List, Set, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.fft import Fragment, Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint import choice
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.choice import (
    FINALISTS,
    CombinationJudge,
    DutyTrial,
    ScoredCombination,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.combinations import CombinationSearch, Rows
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.continuity import (
    ChannelContinuity,
    StemContinuity,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import FitTarget
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import (
    Slot,
    StemLayout,
    separate_layouts,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from sampletones_shared.array import to_numpy
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..conftest import JOINT_PULSE_VOLUMES, JOINT_SIGNAL_LENGTH, rendered_fragment
from .conftest import heard_alone, library_matcher, played_lines

PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
PITCHES: Final[FrozenSet[int]] = frozenset({64, 67})
VOLUMES: Final[FrozenSet[int]] = frozenset({4, 8, 12})
DUTY_CYCLES: Final[FrozenSet[int]] = frozenset({1, 3})
PITCH: Final[int] = 64
OTHER_PITCH: Final[int] = 67
UNDER_PITCH: Final[int] = 57
LOUD: Final[int] = 12
HALF: Final[int] = 8
QUIET: Final[int] = 4
WRITTEN_DUTY: Final[int] = 1
MIRRORED_DUTY: Final[int] = 3
EXACT_TOLERANCE: Final[float] = 0.0
STRONG_INERTIA: Final[float] = 100.0
OWN_COST: Final[float] = 0.0
ONSET_DUTY: Final[int] = 2
RESTS: Final[int] = 6
HELD_FRAMES: Final[int] = 6
CURVED_GAMMA: Final[int] = 50
LOUDER_DRIVE: Final[float] = 2.0
SOFTER_DRIVE: Final[float] = 0.5


def _pulse(pitch: int, volume: int, duty_cycle: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)


LEAD: Final[PulseInstruction] = _pulse(PITCH, LOUD, WRITTEN_DUTY)
DRIVEN_LEAD: Final[PulseInstruction] = _pulse(PITCH, MAX_VOLUME, ONSET_DUTY)
DRIVEN_UNDER: Final[PulseInstruction] = _pulse(UNDER_PITCH, QUIET, ONSET_DUTY)
HARMONY: Final[PulseInstruction] = _pulse(OTHER_PITCH, HALF, WRITTEN_DUTY)
SILENT: Final[PulseInstruction] = PulseInstruction.null_instruction()


@pytest.fixture(name="pulse_channels", scope="module")
def pulse_channels_fixture(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, PULSES)


@pytest.fixture(name="duty_matcher", scope="module")
def duty_matcher_fixture(
    config: Config,
    window: Window,
    extractor: FeatureExtractor,
    pulse_channels: Dict[ChannelName, GeneratorUnion],
) -> FrameMatcher:
    """The matcher of a library of two pulse notes on the two duty cycles sharing a spectrum."""
    generator = pulse_channels[ChannelName.PULSE1]
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {}
    for instruction in generator.get_possible_instructions():
        kept = not instruction.on or (
            isinstance(instruction, PulseInstruction)
            and instruction.pitch in PITCHES
            and instruction.volume in VOLUMES
            and instruction.duty_cycle in DUTY_CYCLES
        )
        if kept:
            data[instruction] = InstructionLibraryFragment.create(generator, instruction, extractor)

    return ReconstructorWorker(
        config=config,
        window=window,
        channels=pulse_channels,
        library_data=InstructionLibraryData.create(config, data),
        layer_data=(),
        signal_length=JOINT_SIGNAL_LENGTH,
    ).matcher


class _Judging:
    """A frame of two pulses, with the search and the judges of a stem holding both pulses."""

    def __init__(
        self,
        config: Config,
        fragment: Fragment,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
    ) -> None:
        self.config = config
        self.fragment = fragment
        self.matcher = matcher
        self.layout: StemLayout = separate_layouts(StemsConfig.single_entry(StemSettings.covering(PULSES)), channels)[0]
        self.catalog = KindCatalog.build(matcher.candidate_provider, channels[ChannelName.PULSE1])
        self.catalogs = {GeneratorClassName.PULSE_GENERATOR: self.catalog}
        self.weights = np.asarray(to_numpy(matcher.scorer.criterion.weights), dtype=np.float64).reshape(-1)
        self.hearing = heard_alone(self.layout, self.catalogs, matcher.candidate_provider, len(fragment.feature.values))
        target = FitTarget.of(fragment, matcher.scorer.criterion)
        self.search = CombinationSearch(fragment, target, self.layout, self.catalogs, matcher, self.hearing)
        self.judge = self.judged(StemContinuity.free(self.layout, self.catalogs))

    def judged(self, continuity: StemContinuity) -> CombinationJudge:
        """A judge of the frame keeping to ``continuity``."""
        return CombinationJudge(
            self.fragment,
            self.layout,
            self.catalogs,
            self.matcher,
            self.weights,
            self.hearing.driven,
            self.hearing,
            continuity,
        )

    def kept(self, before: InstructionUnion, after: InstructionUnion) -> ChannelContinuity:
        """A pulse between neighbors playing ``before`` and ``after``, kept to them strongly."""
        return ChannelContinuity(
            before=before, after=after, weights=TransitionWeights.of(self.config), inertia=STRONG_INERTIA
        )

    def bound(self, first: ChannelContinuity, second: ChannelContinuity) -> StemContinuity:
        return StemContinuity(layout=self.layout, catalogs=self.catalogs, channels=(first, second))

    def row(self, instruction: PulseInstruction) -> int:
        return self.catalog.rows_by_instruction[instruction]

    def rows(self, first: PulseInstruction, second: PulseInstruction) -> Rows:
        return self.row(first), self.row(second)

    def best(self, candidates: List[Rows]) -> ScoredCombination:
        return self.judge.best(self.search, self.judge.finalists(candidates))

    def sounding(self, rows: Rows) -> Set[Tuple[int, int, int]]:
        """The pitch, volume and duty cycle of every pulse ``rows`` sounds."""
        sounded: Set[Tuple[int, int, int]] = set()
        for row in rows:
            instruction = self.catalog.instructions[row]
            if isinstance(instruction, PulseInstruction) and instruction.on:
                sounded.add((instruction.pitch, instruction.volume, instruction.duty_cycle))

        return sounded


@pytest.fixture(name="judging", scope="module")
def judging_fixture(
    config: Config,
    extractor: FeatureExtractor,
    pulse_channels: Dict[ChannelName, GeneratorUnion],
    duty_matcher: FrameMatcher,
) -> _Judging:
    """A frame of one pulse note."""
    fragment = rendered_fragment(config, extractor, {ChannelName.PULSE1: LEAD})
    return _Judging(config, fragment, pulse_channels, duty_matcher)


@pytest.fixture(name="duet", scope="module")
def duet_fixture(
    config: Config,
    extractor: FeatureExtractor,
    pulse_channels: Dict[ChannelName, GeneratorUnion],
    duty_matcher: FrameMatcher,
) -> _Judging:
    """A frame of two pulse notes."""
    fragment = rendered_fragment(config, extractor, {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY})
    return _Judging(config, fragment, pulse_channels, duty_matcher)


@pytest.fixture(name="onset", scope="module")
def onset_fixture(
    config: Config,
    extractor: FeatureExtractor,
    pulse_channels: Dict[ChannelName, GeneratorUnion],
    joint_matcher: FrameMatcher,
) -> _Judging:
    """The first frame of a pulse note after rests, judged among the joint library's volumes."""
    played = _pulse(PITCH, LOUD, ONSET_DUTY)
    line = [SILENT] * RESTS + [played] * HELD_FRAMES
    audio = played_lines(config, {ChannelName.PULSE1: line}, len(line))
    return _Judging(config, extractor.extract(audio)[RESTS], pulse_channels, joint_matcher)


class _Phasing:
    """A frame judged by a stem of two pulses driven at two and at a half, its features read at gamma fifty.

    The first pulse plays ``DRIVEN_LEAD`` and the second ``DRIVEN_UNDER``. Their library feature values
    over the drive squared would phase the second first, and the transform of their driven powers
    phases the first first.
    """

    def __init__(self, config: Config, channels: Dict[ChannelName, GeneratorUnion]) -> None:
        self.matcher = library_matcher(config, ChannelName.PULSE1, [SILENT, DRIVEN_LEAD, DRIVEN_UNDER])
        provider = self.matcher.candidate_provider
        self.layout = StemLayout(
            stem_id=0,
            slots=(
                Slot(channel_name=ChannelName.PULSE1, kind=GeneratorClassName.PULSE_GENERATOR, drive=LOUDER_DRIVE),
                Slot(channel_name=ChannelName.PULSE2, kind=GeneratorClassName.PULSE_GENERATOR, drive=SOFTER_DRIVE),
            ),
            cap=len(PULSES),
        )
        self.catalog = KindCatalog.build(provider, channels[ChannelName.PULSE1])
        catalogs = {GeneratorClassName.PULSE_GENERATOR: self.catalog}
        extractor = get_feature_extractor(config, Window.from_config(config))
        fragment = rendered_fragment(config, extractor, {ChannelName.PULSE1: LEAD})
        hearing = heard_alone(self.layout, catalogs, provider, len(fragment.feature.values))
        self.weights = np.asarray(to_numpy(self.matcher.scorer.criterion.weights), dtype=np.float64).reshape(-1)
        self.judge = CombinationJudge(
            fragment,
            self.layout,
            catalogs,
            self.matcher,
            self.weights,
            hearing.driven,
            hearing,
            StemContinuity.free(self.layout, catalogs),
        )
        self.rows: Rows = (
            self.catalog.rows_by_instruction[DRIVEN_LEAD],
            self.catalog.rows_by_instruction[DRIVEN_UNDER],
        )

    def driven_loudness(self, place: int) -> float:
        """The criterion's weighting of the transform of the row's power at its pulse's drive."""
        drive = self.layout.slots[place].drive
        return float(self._features(self.catalog.powers[self.rows[place]] / drive**2) @ self.weights)

    def library_loudness(self, place: int) -> float:
        """The criterion's weighting of the row's library feature values, over its pulse's drive squared."""
        drive = self.layout.slots[place].drive
        return float(self._features(self.catalog.powers[self.rows[place]]) @ self.weights) / drive**2

    def alone(self, place: int) -> Rows:
        """The rows with every pulse but the one at ``place`` silenced."""
        return tuple(row if index == place else self.catalog.silence for index, row in enumerate(self.rows))

    def _features(self, power: np.ndarray) -> np.ndarray:
        return np.asarray(to_numpy(self.matcher.candidate_provider.features_of(power)), dtype=np.float64)


@pytest.fixture(name="phasing", scope="module")
def phasing_fixture(pulse_channels: Dict[ChannelName, GeneratorUnion]) -> _Phasing:
    return _Phasing(Config(library=InstructionsLibraryConfig(transformation_gamma=CURVED_GAMMA)), pulse_channels)


class TestTheOrderOfPhasing(BaseTestSuite):
    """Channels are phased loudest first by the criterion's weighting of each row heard alone at its drive.

    At a transformation gamma of fifty the features read power through a curve, so a row's loudness
    at a drive is the weighted transform of its power at that drive, which reverses the order its
    library feature values over the drive squared give.
    """

    def test_pulses_driven_apart_are_phased_in_the_order_of_the_transform_of_their_driven_powers(
        self, phasing: _Phasing
    ) -> None:
        driven = [phasing.driven_loudness(place) for place in range(len(PULSES))]
        library = [phasing.library_loudness(place) for place in range(len(PULSES))]
        louder = int(np.argmax(driven))

        both, louder_alone = phasing.judge.scored([phasing.rows, phasing.alone(louder)])

        assert int(np.argmax(library)) != louder
        assert both.contributions[louder] is louder_alone.contributions[louder]


class TestScoringACombination(BaseTestSuite):
    def test_a_combination_is_weighed_by_its_cost_and_the_charge_its_channels_pay(self, judging: _Judging) -> None:
        first, second = judging.kept(LEAD, LEAD), judging.kept(SILENT, SILENT)
        rows = judging.rows(HARMONY, SILENT)

        (bound,) = judging.judged(judging.bound(first, second)).scored([rows])
        (free,) = judging.judge.scored([rows])

        breaking_least = min(first.charge(HARMONY), first.charge(SILENT) + second.charge(HARMONY))
        assert bound.charge == pytest.approx(breaking_least)
        assert bound.cost == free.cost
        assert bound.weighed == pytest.approx(free.cost + breaking_least)

    def test_a_frame_heard_alone_charges_nothing(self, judging: _Judging) -> None:
        (scored,) = judging.judge.scored([judging.rows(HARMONY, LEAD)])

        assert scored.charge == 0.0
        assert scored.weighed == scored.cost

    def test_the_louder_channel_is_phased_first_and_keeps_its_phase_behind_nothing(self, duet: _Judging) -> None:
        """A channel phased behind the same louder rows keeps its phase for every combination sharing them."""
        loud_alone, both = duet.judge.scored([duet.rows(SILENT, LEAD), duet.rows(HARMONY, LEAD)])

        assert both.contributions[1] is loud_alone.contributions[1]
        assert both.contributions[0] is not None

    def test_a_silent_channel_adds_nothing(self, judging: _Judging) -> None:
        (scored,) = judging.judge.scored([judging.rows(SILENT, SILENT)])

        assert scored.contributions == (None, None)


class TestTheFinalists(BaseTestSuite):
    @pytest.fixture(name="candidates")
    def candidates_fixture(self, judging: _Judging) -> List[Rows]:
        """More distinct combinations than the judge keeps, none of them the pair the neighbors play."""
        sounding = [row for row in range(len(judging.catalog.instructions)) if judging.catalog.sounding(row)]
        return [(row, judging.catalog.silence) for row in sounding[: FINALISTS + 2]]

    def test_the_finalists_are_the_spectral_ranking_s_cheapest(self, judging: _Judging, candidates: List[Rows]) -> None:
        finalists = judging.judge.finalists(candidates)

        assert [finalist.rows for finalist in finalists] == candidates[:FINALISTS]

    def test_where_the_charge_binds_the_neighbors_combinations_join_the_finalists(
        self, judging: _Judging, candidates: List[Rows]
    ) -> None:
        judge = judging.judged(judging.bound(judging.kept(LEAD, LEAD), judging.kept(HARMONY, HARMONY)))

        finalists = judge.finalists(candidates)

        assert [finalist.rows for finalist in finalists] == [*candidates[:FINALISTS], judging.rows(LEAD, HARMONY)]

    def test_a_neighbors_combination_among_the_cheapest_stands_once(self, judging: _Judging) -> None:
        neighbors = judging.rows(LEAD, SILENT)
        judge = judging.judged(judging.bound(judging.kept(LEAD, LEAD), judging.kept(SILENT, SILENT)))

        finalists = judge.finalists([neighbors])

        assert [finalist.rows for finalist in finalists] == [neighbors]

    def test_a_strong_inertia_holds_the_choice_to_what_the_neighbors_play(self, judging: _Judging) -> None:
        judge = judging.judged(judging.bound(judging.kept(HARMONY, HARMONY), judging.kept(SILENT, SILENT)))

        best = judge.best(judging.search, judge.finalists([judging.rows(LEAD, SILENT)]))

        assert judging.sounding(best.rows) == {(OTHER_PITCH, HALF, WRITTEN_DUTY)}


class TestTheChoice(BaseTestSuite):
    def test_a_quiet_pulse_the_frame_lacks_is_silenced(self, judging: _Judging) -> None:
        best = judging.best([judging.rows(LEAD, _pulse(OTHER_PITCH, QUIET, WRITTEN_DUTY))])

        assert judging.sounding(best.rows) == {(PITCH, LOUD, WRITTEN_DUTY)}

    def test_both_notes_of_a_frame_playing_two_stay(self, duet: _Judging) -> None:
        best = duet.best([duet.rows(LEAD, HARMONY)])

        assert duet.sounding(best.rows) == {(PITCH, LOUD, WRITTEN_DUTY), (OTHER_PITCH, HALF, WRITTEN_DUTY)}

    def test_a_note_split_over_both_pulses_gathers_on_one_at_the_volume_it_sounds(self, judging: _Judging) -> None:
        half = judging.row(_pulse(PITCH, HALF, WRITTEN_DUTY))

        best = judging.best([(half, half)])

        assert judging.sounding(best.rows) == {(PITCH, LOUD, WRITTEN_DUTY)}
        assert sum(judging.catalog.sounding(row) for row in best.rows) == 1

    def test_a_channel_left_after_a_silence_tries_the_volumes_beside_the_one_the_spectral_term_prefers(
        self, onset: _Judging
    ) -> None:
        """The first frame of a note after rests reads a window reaching back into the silence.

        So the spectral term prefers a volume quieter than the note plays, while the waveform hears the
        played one. Thinning the note split over both pulses leaves one pulse, which the releveling
        offers the volumes nearest the spectral term's, the played one among them.
        """
        volumes = sorted(JOINT_PULSE_VOLUMES)
        alone = [onset.rows(_pulse(PITCH, volume, ONSET_DUTY), SILENT) for volume in volumes]
        preferred = volumes[int(np.argmin(onset.search.spectral_costs(alone)))]
        split = onset.row(_pulse(PITCH, HALF, ONSET_DUTY))

        best = onset.best([(split, split)])

        assert preferred < LOUD
        assert onset.sounding(best.rows) == {(PITCH, LOUD, ONSET_DUTY)}

    def test_a_pulse_tries_the_duty_cycle_sharing_its_spectrum_however_far_the_spectral_term_sets_them(
        self, judging: _Judging, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(choice, "TIMBRE_TOLERANCE", EXACT_TOLERANCE)

        best = judging.best([judging.rows(_pulse(PITCH, LOUD, MIRRORED_DUTY), SILENT)])

        assert judging.sounding(best.rows) == {(PITCH, LOUD, WRITTEN_DUTY)}

    def test_the_choice_is_the_first_of_finalists_weighed_alike(self, judging: _Judging) -> None:
        """Pulses driven alike sound a combination the same in either order, so its two orders weigh alike."""
        finalists = judging.judge.scored([judging.rows(LEAD, SILENT), judging.rows(SILENT, LEAD)])

        best = judging.judge.best(judging.search, finalists)

        assert finalists[0].weighed == finalists[1].weighed
        assert best.rows == finalists[0].rows


class TestADutyTrial(BaseTestSuite):
    """The spectral term hears duty cycles alike where they share a spectrum or cost nearly alike."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        shares_spectrum: bool
        distance: float

    test_cases: Tuple["TestADutyTrial.TestCase", ...] = (
        TestCase(label="sharing-the-spectrum-far-off", shares_spectrum=True, distance=4.0, expected=True),
        TestCase(label="unlike-within-the-tolerance", shares_spectrum=False, distance=0.5, expected=True),
        TestCase(label="unlike-cheaper-within-the-tolerance", shares_spectrum=False, distance=-0.5, expected=True),
        TestCase(label="unlike-at-the-tolerance", shares_spectrum=False, distance=1.0, expected=True),
        TestCase(label="unlike-beyond-the-tolerance", shares_spectrum=False, distance=1.5, expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_trial_is_left_to_the_waveform_within_the_tolerance_or_sharing_the_spectrum(
        self, test_case: TestCase
    ) -> None:
        trial = DutyTrial(rows=(), shares_spectrum=test_case.shares_spectrum)
        cost = OWN_COST + test_case.distance * choice.TIMBRE_TOLERANCE

        assert trial.left_to_waveform(cost, OWN_COST) == test_case.expected


class TestThePool(BaseTestSuite):
    """The judge pools the combinations a decoder over whole combinations reads, each once."""

    @dataclass(frozen=True)
    class Pooled:
        winner: ScoredCombination
        finalist: ScoredCombination
        previous: Rows
        pooled: List[Rows]

    @pytest.fixture(name="pooled")
    def pooled_fixture(self, judging: _Judging) -> "TestThePool.Pooled":
        winner, finalist, swapped = judging.judge.scored(
            [
                judging.rows(LEAD, _pulse(OTHER_PITCH, QUIET, WRITTEN_DUTY)),
                judging.rows(_pulse(PITCH, HALF, WRITTEN_DUTY), HARMONY),
                judging.rows(_pulse(OTHER_PITCH, QUIET, WRITTEN_DUTY), LEAD),
            ]
        )
        previous = judging.rows(SILENT, _pulse(OTHER_PITCH, LOUD, WRITTEN_DUTY))
        combinations = judging.judge.pooled(judging.search, [winner, finalist, swapped], winner, previous)
        return self.Pooled(
            winner=winner,
            finalist=finalist,
            previous=previous,
            pooled=[judging.search.canonical(combination.rows) for combination in combinations],
        )

    def test_the_winner_comes_first_then_the_finalists(self, pooled: "TestThePool.Pooled", judging: _Judging) -> None:
        canonical = judging.search.canonical
        assert pooled.pooled[:2] == [canonical(pooled.winner.rows), canonical(pooled.finalist.rows)]

    def test_every_set_of_the_winner_s_channels_is_pooled_silenced(
        self, pooled: "TestThePool.Pooled", judging: _Judging
    ) -> None:
        first, second = pooled.winner.rows
        silence = judging.catalog.silence

        for silenced in [(silence, second), (first, silence), (silence, silence)]:
            assert judging.search.canonical(silenced) in pooled.pooled

    def test_each_finalist_is_pooled_with_each_channel_silenced(
        self, pooled: "TestThePool.Pooled", judging: _Judging
    ) -> None:
        first, second = pooled.finalist.rows
        silence = judging.catalog.silence

        for silenced in [(silence, second), (first, silence)]:
            assert judging.search.canonical(silenced) in pooled.pooled

    def test_the_previous_frame_s_winner_is_pooled(self, pooled: "TestThePool.Pooled", judging: _Judging) -> None:
        assert judging.search.canonical(pooled.previous) in pooled.pooled

    def test_every_combination_reads_once_whatever_its_pulses_order(self, pooled: "TestThePool.Pooled") -> None:
        assert len(pooled.pooled) == len(set(pooled.pooled))

    def test_after_a_rest_the_pool_holds_no_previous_winner(self, judging: _Judging) -> None:
        winner = judging.judge.scored([judging.rows(LEAD, SILENT)])[0]
        previous = judging.rows(SILENT, _pulse(OTHER_PITCH, LOUD, WRITTEN_DUTY))

        with_previous = judging.judge.pooled(judging.search, [winner], winner, previous)
        after_rest = judging.judge.pooled(judging.search, [winner], winner, None)

        assert len(with_previous) == len(after_rest) + 1
