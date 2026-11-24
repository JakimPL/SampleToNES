from dataclasses import replace
from typing import Dict, Final, List, Mapping

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint import combinations
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog, RowSound
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.combinations import (
    DISTINCT_COMBINATIONS,
    SILENT_ENTRY,
    ChannelUnits,
    Choice,
    CombinationSearch,
    Rows,
    searched_choices,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.fit import FitTarget
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.hearing import (
    SequenceHearing,
    heard_features,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import Slot, StemLayout
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.proposals import (
    NoteDictionary,
    proposed_rows,
)
from sampletones_core.reconstructions.reconstructor.window.surroundings import HeldNote, TonalSurroundings
from sampletones_shared.array import xp
from tests.suite.base import BaseTestSuite

from ..conftest import rendered_fragment
from .conftest import heard_alone, library_matcher

PULSE: Final[GeneratorClassName] = GeneratorClassName.PULSE_GENERATOR
TRIANGLE: Final[GeneratorClassName] = GeneratorClassName.TRIANGLE_GENERATOR
NOISE: Final[GeneratorClassName] = GeneratorClassName.NOISE_GENERATOR
KINDS: Final[Dict[ChannelName, GeneratorClassName]] = {
    ChannelName.PULSE1: PULSE,
    ChannelName.PULSE2: PULSE,
    ChannelName.TRIANGLE: TRIANGLE,
    ChannelName.NOISE: NOISE,
}
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
HIT: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=15, short=False)
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: HARMONY,
    ChannelName.TRIANGLE: BASS,
}
FIRST: Final[int] = 10
SECOND: Final[int] = 11
THIRD: Final[int] = 12
TONE: Final[int] = 20
SHAPE: Final[int] = 30
OFFERED: Final[Dict[GeneratorClassName, List[int]]] = {
    PULSE: [FIRST, SECOND, THIRD],
    TRIANGLE: [TONE],
    NOISE: [SHAPE],
}
LOUDER_DRIVE: Final[float] = 2.0
COST_ROUNDING: Final[float] = 1e-9
LINEAR_GAMMA: Final[int] = 0
CURVED_GAMMA: Final[int] = 50
LEAK_SHARE: Final[float] = 0.5


def _layout(channels: List[ChannelName], cap: int) -> StemLayout:
    """A stem of ``channels`` at unit drive, sounding at most ``cap`` of them."""
    slots = tuple(Slot(channel_name=name, kind=KINDS[name], drive=UNIT_DRIVE) for name in channels)
    return StemLayout(stem_id=0, slots=slots, cap=cap)


def _driven(layout: StemLayout, place: int, drive: float) -> StemLayout:
    """``layout`` with the channel at ``place`` driven at ``drive``."""
    slots = list(layout.slots)
    slots[place] = replace(slots[place], drive=drive)
    return replace(layout, slots=tuple(slots))


EVERY_CHANNEL: Final[List[ChannelName]] = list(KINDS)
PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]


@pytest.fixture(name="catalogs", scope="module")
def catalogs_fixture(
    joint_matcher: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]
) -> Dict[GeneratorClassName, KindCatalog]:
    provider = joint_matcher.candidate_provider
    return {
        KINDS[name]: KindCatalog.build(provider, all_channels[name])
        for name in (ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE)
    }


@pytest.fixture(name="chord", scope="module")
def chord_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, CHORD)


@pytest.fixture(name="lead", scope="module")
def lead_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {ChannelName.PULSE1: LEAD})


@pytest.fixture(name="hit", scope="module")
def hit_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {ChannelName.NOISE: HIT})


@pytest.fixture(name="silence", scope="module")
def silence_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {})


def _search(
    fragment: Fragment, layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], matcher: FrameMatcher
) -> CombinationSearch:
    """The search of ``fragment`` heard alone on ``layout``'s channels."""
    hearing = heard_alone(layout, catalogs, matcher.candidate_provider, len(fragment.feature.values))
    target = FitTarget.of(fragment, matcher.scorer.criterion)
    return CombinationSearch(fragment, target, layout, catalogs, matcher, hearing)


def _proposed(
    fragment: Fragment, layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], matcher: FrameMatcher
) -> Dict[GeneratorClassName, List[int]]:
    hearing = heard_alone(layout, catalogs, matcher.candidate_provider, len(fragment.feature.values))
    target = FitTarget.of(fragment, matcher.scorer.criterion)
    return proposed_rows(
        fragment, target, layout, NoteDictionary.of(layout, catalogs).heard(hearing), catalogs, matcher, hearing
    )


def _played(
    layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], played: Mapping[ChannelName, InstructionUnion]
) -> Rows:
    """The rows playing ``played`` on ``layout``'s channels, silence on the channels it leaves out."""
    rows: List[int] = []
    for slot in layout.slots:
        catalog = catalogs[slot.kind]
        instruction = played.get(slot.channel_name)
        rows.append(catalog.silence if instruction is None else catalog.rows_by_instruction[instruction])

    return tuple(rows)


def _sounding(layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], rows: Rows) -> int:
    return sum(catalogs[slot.kind].sounding(row) for slot, row in zip(layout.slots, rows))


class TestTheSearchedChoices(BaseTestSuite):
    """Every set of proposals each kind's channels may sound, crossed over the kinds within the stem's count."""

    def test_every_set_of_proposals_within_the_channels_is_searched_once(self) -> None:
        pulse_sets = [
            (None, None),
            (FIRST, None),
            (SECOND, None),
            (THIRD, None),
            (FIRST, SECOND),
            (FIRST, THIRD),
            (SECOND, THIRD),
        ]

        choices = searched_choices(_layout(EVERY_CHANNEL, cap=4), OFFERED)

        expected = {(*pulses, tone, shape) for pulses in pulse_sets for tone in (None, TONE) for shape in (None, SHAPE)}
        assert len(choices) == len(expected)
        assert set(choices) == expected

    def test_silence_on_every_channel_is_searched_first(self) -> None:
        assert searched_choices(_layout(EVERY_CHANNEL, cap=4), OFFERED)[0] == (None, None, None, None)

    def test_a_kind_s_sets_stand_silence_first_then_smaller_sets_then_proposal_order(self) -> None:
        choices = searched_choices(_layout(PULSES, cap=2), OFFERED)

        assert choices == [
            (None, None),
            (FIRST, None),
            (SECOND, None),
            (THIRD, None),
            (FIRST, SECOND),
            (FIRST, THIRD),
            (SECOND, THIRD),
        ]

    def test_the_first_kind_by_name_varies_slowest(self) -> None:
        choices = searched_choices(_layout([ChannelName.PULSE1, ChannelName.NOISE], cap=2), OFFERED)

        assert choices == [
            (None, None),
            (FIRST, None),
            (SECOND, None),
            (THIRD, None),
            (None, SHAPE),
            (FIRST, SHAPE),
            (SECOND, SHAPE),
            (THIRD, SHAPE),
        ]

    def test_pulses_driven_alike_sound_each_set_once_on_the_pulses_in_layout_order(self) -> None:
        choices = searched_choices(_layout(PULSES, cap=2), OFFERED)

        assert (FIRST, SECOND) in choices
        assert (SECOND, FIRST) not in choices
        assert (None, FIRST) not in choices

    @pytest.mark.parametrize("cap", [1, 2, 3], ids=["one", "two", "three"])
    def test_no_choice_sounds_more_channels_than_the_stem_s_count(self, cap: int) -> None:
        every = searched_choices(_layout(EVERY_CHANNEL, cap=4), OFFERED)

        choices = searched_choices(_layout(EVERY_CHANNEL, cap=cap), OFFERED)

        assert choices == [choice for choice in every if _count(choice) <= cap]

    def test_a_stem_counted_to_one_channel_chooses_one_proposal_or_silence(self) -> None:
        choices = searched_choices(_layout(EVERY_CHANNEL, cap=1), OFFERED)

        assert choices[0] == (None, None, None, None)
        assert len(choices) == 1 + len(OFFERED[PULSE]) + len(OFFERED[TRIANGLE]) + len(OFFERED[NOISE])

    def test_an_empty_proposal_set_leaves_silence_alone(self) -> None:
        assert searched_choices(_layout(EVERY_CHANNEL, cap=4), {}) == [(None, None, None, None)]

    def test_a_stem_of_one_channel_chooses_each_proposal_or_silence(self) -> None:
        choices = searched_choices(_layout([ChannelName.PULSE1], cap=1), OFFERED)

        assert choices == [(None,), (FIRST,), (SECOND,), (THIRD,)]


def _count(choice: Choice) -> int:
    return sum(row is not None for row in choice)


class TestChannelUnits(BaseTestSuite):
    """A fitted channel's silence and each proposal's unit, its cap at full volume and its start at its own volume."""

    QUIET: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=8, duty_cycle=2)

    @pytest.fixture(name="units")
    def units_fixture(
        self, lead: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> ChannelUnits:
        pulses = catalogs[PULSE]
        layout = _layout([ChannelName.PULSE1], cap=1)
        hearing = heard_alone(layout, catalogs, joint_matcher.candidate_provider, len(lead.feature.values))
        choices: List[Choice] = [
            (None,),
            (pulses.rows_by_instruction[self.QUIET],),
            (pulses.rows_by_instruction[HARMONY],),
        ]
        return ChannelUnits.of(choices, 0, pulses, hearing, len(lead.feature.values))

    def test_a_silent_choice_holds_the_silent_entry_and_the_proposals_theirs_in_row_order(
        self, units: ChannelUnits, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        pulses = catalogs[PULSE]
        quiet, harmony = pulses.rows_by_instruction[self.QUIET], pulses.rows_by_instruction[HARMONY]

        assert units.entries[0] == SILENT_ENTRY
        assert (units.entries[1] < units.entries[2]) == (quiet < harmony)
        assert set(units.entries[1:].tolist()) == {SILENT_ENTRY + 1, SILENT_ENTRY + 2}

    def test_a_proposal_s_unit_is_its_note_s_loudest_row_in_its_timbre(
        self, units: ChannelUnits, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        pulses = catalogs[PULSE]
        quiet = pulses.rows_by_instruction[self.QUIET]

        assert units.units[quiet] == pulses.unit_of(quiet)

    def test_a_proposal_starts_at_its_own_volume_and_reaches_at_most_full_volume(
        self, units: ChannelUnits, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        quiet = catalogs[PULSE].rows_by_instruction[self.QUIET]
        entry = int(units.entries[1])
        unit = units.units[quiet]

        assert units.starts[entry] == pytest.approx(unit.level_of(self.QUIET.volume))
        assert units.caps[entry] == pytest.approx(unit.full_level)

    def test_a_proposal_s_unit_is_heard_as_the_frame_s_fit_reads_it(
        self,
        units: ChannelUnits,
        lead: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        layout = _layout([ChannelName.PULSE1], cap=1)
        hearing = heard_alone(layout, catalogs, joint_matcher.candidate_provider, len(lead.feature.values))
        quiet = catalogs[PULSE].rows_by_instruction[self.QUIET]
        entry = int(units.entries[1])

        assert np.array_equal(units.features[entry], hearing.unit_features(0, [units.units[quiet].row])[0])
        assert np.array_equal(units.powers[entry], hearing.unit_powers(0, [units.units[quiet].row])[0])

    def test_silence_holds_no_power_and_no_level(self, units: ChannelUnits) -> None:
        assert not units.features[SILENT_ENTRY].any()
        assert not units.powers[SILENT_ENTRY].any()
        assert (units.caps[SILENT_ENTRY], units.starts[SILENT_ENTRY]) == (0.0, 0.0)


@pytest.fixture(name="curved", scope="module", params=[LINEAR_GAMMA, CURVED_GAMMA], ids=["gamma_0", "gamma_50"])
def curved_fixture(request: pytest.FixtureRequest) -> FrameMatcher:
    """The matcher of a library of the bass and its silence, its features read at the gamma given."""
    config = Config(library=InstructionsLibraryConfig(transformation_gamma=request.param))
    return library_matcher(config, ChannelName.TRIANGLE, [TriangleInstruction.null_instruction(), BASS])


class TestTheFixedParts(BaseTestSuite):
    """Every choice's fixed part: the leak and its one-level channels' rows, added in power.

    A fixed part reads the transform of the power it holds, as the frame reads its sum, at a
    transformation gamma of zero, which reads power linearly, and at fifty, which reads it through a
    curve. The case's frame stands beside neighbors leaving part of the bass's power in its window.
    """

    def test_a_fixed_part_reads_the_transform_of_the_power_it_holds(
        self, curved: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        provider = curved.candidate_provider
        catalogs = {TRIANGLE: KindCatalog.build(provider, all_channels[ChannelName.TRIANGLE])}
        layout = _layout([ChannelName.TRIANGLE], cap=1)
        bass = catalogs[TRIANGLE].rows_by_instruction[BASS]
        bins = int(catalogs[TRIANGLE].powers.shape[1])
        leak = LEAK_SHARE * catalogs[TRIANGLE].powers[bass]
        beside = TonalSurroundings(
            leak=leak, before=HeldNote.silence(bins), after=HeldNote.silence(bins), own=np.ones(bins)
        )
        hearing = SequenceHearing.of(layout, catalogs, [beside], provider)
        frame = rendered_fragment(provider.config, provider.extractor, {ChannelName.TRIANGLE: BASS})
        search = CombinationSearch(
            frame, FitTarget.of(frame, curved.scorer.criterion), layout, catalogs, curved, hearing
        )

        features, powers = search.fixed_parts([(None,), (bass,)])

        held = np.stack([leak, leak + hearing.powers(0, [bass])[0]])
        assert powers == pytest.approx(held)
        assert features == pytest.approx(heard_features(provider, held))


class TestFittingTheChoices(BaseTestSuite):
    """The choices fitted at once, the cheapest fits moved onto the rows nearest their levels."""

    def test_a_chord_s_notes_play_on_their_own_kinds_in_the_cheapest_combination_reached(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=4)
        search = _search(chord, layout, catalogs, joint_matcher)

        cheapest = search.refined(search.fitted(_proposed(chord, layout, catalogs, joint_matcher)))[0]

        assert search.canonical(cheapest.rows) == search.canonical(_played(layout, catalogs, CHORD))

    def test_the_fitted_combinations_are_distinct_whatever_their_pulses_order(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=4)
        search = _search(chord, layout, catalogs, joint_matcher)

        fitted = search.fitted(_proposed(chord, layout, catalogs, joint_matcher))

        assert 1 < len(fitted) <= DISTINCT_COMBINATIONS
        assert len({search.canonical(rows) for rows in fitted}) == len(fitted)

    def test_the_scan_stops_once_enough_combinations_stand(
        self,
        chord: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(combinations, "DISTINCT_COMBINATIONS", 2)
        layout = _layout(EVERY_CHANNEL, cap=4)
        search = _search(chord, layout, catalogs, joint_matcher)

        assert len(search.fitted(_proposed(chord, layout, catalogs, joint_matcher))) == 2

    def test_a_fitted_level_lands_on_the_row_nearest_the_volume_it_sounds(
        self, lead: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        """A proposal too quiet for the frame is fitted up to the volume the frame plays."""
        layout = _layout([ChannelName.PULSE1], cap=1)
        quiet = PulseInstruction(on=True, pitch=LEAD.pitch, volume=4, duty_cycle=LEAD.duty_cycle)
        search = _search(lead, layout, catalogs, joint_matcher)

        fitted = search.fitted({PULSE: [catalogs[PULSE].rows_by_instruction[quiet]]})

        assert fitted[0] == _played(layout, catalogs, {ChannelName.PULSE1: LEAD})

    def test_a_choice_s_triangle_sounds_in_its_fit_at_its_one_level(
        self,
        config: Config,
        extractor: FeatureExtractor,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        layout = _layout([ChannelName.PULSE1, ChannelName.TRIANGLE], cap=2)
        bass = rendered_fragment(config, extractor, {ChannelName.TRIANGLE: BASS})
        search = _search(bass, layout, catalogs, joint_matcher)

        fitted = search.fitted(_proposed(bass, layout, catalogs, joint_matcher))

        assert fitted[0] == _played(layout, catalogs, {ChannelName.TRIANGLE: BASS})

    def test_an_empty_proposal_set_fits_silence_alone(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=4)

        fitted = _search(chord, layout, catalogs, joint_matcher).fitted({})

        assert fitted == [_played(layout, catalogs, {})]

    def test_silence_fits_a_silent_frame_best(
        self, silence: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=4)
        search = _search(silence, layout, catalogs, joint_matcher)

        fitted = search.fitted(_proposed(silence, layout, catalogs, joint_matcher))

        assert fitted[0] == _played(layout, catalogs, {})

    def test_a_stem_counted_to_one_channel_fits_and_refines_combinations_sounding_one(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=1)
        search = _search(chord, layout, catalogs, joint_matcher)

        fitted = search.fitted(_proposed(chord, layout, catalogs, joint_matcher))
        refined = search.refined(fitted)

        assert all(_sounding(layout, catalogs, rows) <= 1 for rows in fitted)
        assert all(_sounding(layout, catalogs, combination.rows) <= 1 for combination in refined)


class TestRefiningCombinations(BaseTestSuite):
    """Each sounding channel in turn moves to the row of its note, or its silence, sounding best with the rest."""

    @pytest.mark.parametrize("volume, duty_cycle", [(4, 2), (12, 1)], ids=["volume", "duty_cycle"])
    def test_a_channel_moves_to_the_volume_and_duty_cycle_the_frame_plays(
        self,
        volume: int,
        duty_cycle: int,
        lead: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        layout = _layout([ChannelName.PULSE1], cap=1)
        start = PulseInstruction(on=True, pitch=LEAD.pitch, volume=volume, duty_cycle=duty_cycle)

        (refined,) = _search(lead, layout, catalogs, joint_matcher).refined(
            [_played(layout, catalogs, {ChannelName.PULSE1: start})]
        )

        assert refined.rows == _played(layout, catalogs, {ChannelName.PULSE1: LEAD})

    def test_a_note_the_frame_lacks_falls_silent(
        self, lead: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(PULSES, cap=2)
        extra = PulseInstruction(on=True, pitch=HARMONY.pitch, volume=15, duty_cycle=2)

        (refined,) = _search(lead, layout, catalogs, joint_matcher).refined(
            [_played(layout, catalogs, {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: extra})]
        )

        assert refined.rows == _played(layout, catalogs, {ChannelName.PULSE1: LEAD})

    def test_a_silent_channel_stays_silent(
        self, lead: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        """A move starts from a sounding row, so a combination keeps within the stem's count of channels."""
        layout = _layout(PULSES, cap=2)
        silent = _played(layout, catalogs, {})

        (refined,) = _search(lead, layout, catalogs, joint_matcher).refined([silent])

        assert refined.rows == silent

    def test_the_noise_moves_to_any_shape_it_holds(
        self, hit: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout([ChannelName.NOISE], cap=1)
        other_shape = NoiseInstruction(on=True, period=8, volume=HIT.volume, short=False)

        (refined,) = _search(hit, layout, catalogs, joint_matcher).refined(
            [_played(layout, catalogs, {ChannelName.NOISE: other_shape})]
        )

        assert catalogs[NOISE].notes[refined.rows[0]] == RowSound.of(HIT).note

    def test_the_triangle_falls_silent_where_the_frame_lacks_it(
        self, lead: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout([ChannelName.PULSE1, ChannelName.TRIANGLE], cap=2)
        extra = TriangleInstruction(on=True, pitch=57)

        (refined,) = _search(lead, layout, catalogs, joint_matcher).refined(
            [_played(layout, catalogs, {ChannelName.PULSE1: LEAD, ChannelName.TRIANGLE: extra})]
        )

        assert refined.rows == _played(layout, catalogs, {ChannelName.PULSE1: LEAD})

    @pytest.mark.parametrize("lead_first", [True, False], ids=["lead_first", "harmony_first"])
    def test_both_orders_of_pulses_driven_alike_read_once_the_first_given_standing(
        self,
        lead_first: bool,
        chord: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        joint_matcher: FrameMatcher,
    ) -> None:
        layout = _layout(PULSES, cap=2)
        ordered = _played(layout, catalogs, {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY})
        swapped = (ordered[1], ordered[0])
        given = [ordered, swapped] if lead_first else [swapped, ordered]

        refined = _search(chord, layout, catalogs, joint_matcher).refined(given)

        assert [combination.rows for combination in refined] == [given[0]]

    def test_combinations_come_cheapest_first_each_at_its_spectral_cost(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=4)
        search = _search(chord, layout, catalogs, joint_matcher)

        refined = search.refined(search.fitted(_proposed(chord, layout, catalogs, joint_matcher)))

        costs = [combination.cost for combination in refined]
        assert costs == sorted(costs)
        assert costs == pytest.approx(search.spectral_costs([combination.rows for combination in refined]).tolist())

    def test_nothing_to_refine_reaches_nothing(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        assert not _search(chord, _layout(PULSES, cap=2), catalogs, joint_matcher).refined([])


class TestScoringCombinations(BaseTestSuite):
    def test_a_combination_s_spectral_cost_is_the_frame_s_with_its_rows_heard_together(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout(EVERY_CHANNEL, cap=4)
        hearing = heard_alone(layout, catalogs, joint_matcher.candidate_provider, len(chord.feature.values))
        rows = _played(layout, catalogs, CHORD)

        cost = _search(chord, layout, catalogs, joint_matcher).spectral_costs([rows])[0]

        power = sum((hearing.powers(place, [row])[0] for place, row in enumerate(rows)), hearing.leak)
        features = joint_matcher.candidate_provider.features_of(xp.asarray(power[None, :]))
        expected = joint_matcher.scorer.spectral_costs(chord, features)[0]
        assert cost == pytest.approx(expected, abs=COST_ROUNDING)

    def test_pulses_driven_alike_read_in_one_order(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        search = _search(chord, _layout(EVERY_CHANNEL, cap=4), catalogs, joint_matcher)

        assert search.canonical((SECOND, FIRST, TONE, SHAPE)) == (FIRST, SECOND, TONE, SHAPE)
        assert search.canonical((FIRST, SECOND, TONE, SHAPE)) == (FIRST, SECOND, TONE, SHAPE)

    def test_pulses_driven_apart_keep_their_order(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _driven(_layout(PULSES, cap=2), 0, LOUDER_DRIVE)

        assert _search(chord, layout, catalogs, joint_matcher).canonical((SECOND, FIRST)) == (SECOND, FIRST)

    def test_a_lone_pulse_keeps_its_row(
        self, chord: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], joint_matcher: FrameMatcher
    ) -> None:
        layout = _layout([ChannelName.PULSE1, ChannelName.TRIANGLE], cap=2)

        assert _search(chord, layout, catalogs, joint_matcher).canonical((SECOND, TONE)) == (SECOND, TONE)
