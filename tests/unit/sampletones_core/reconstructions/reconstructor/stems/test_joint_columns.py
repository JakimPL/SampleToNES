from dataclasses import dataclass
from typing import Dict, Final, List, Set

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.choice import (
    CombinationJudge,
    ScoredCombination,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.columns import (
    VOLUME_NEIGHBORS,
    ChannelColumns,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.continuity import StemContinuity
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.hearing import SteadyHearing
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_shared.array import to_numpy, xp
from tests.suite.base import BaseTestSuite

from ..conftest import rendered_fragment
from .conftest import heard_alone

PULSE: Final[GeneratorClassName] = GeneratorClassName.PULSE_GENERATOR
TRIANGLE: Final[GeneratorClassName] = GeneratorClassName.TRIANGLE_GENERATOR
NOISE: Final[GeneratorClassName] = GeneratorClassName.NOISE_GENERATOR
EVERY_CHANNEL: Final[List[ChannelName]] = ChannelName.items()
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
FULL_LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=15, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
FIRST_OTHER: Final[PulseInstruction] = PulseInstruction(on=True, pitch=60, volume=12, duty_cycle=2)
SECOND_OTHER: Final[PulseInstruction] = PulseInstruction(on=True, pitch=57, volume=8, duty_cycle=1)
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
OTHER_BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=45)
HIT: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=15, short=False)
SILENT_NOISE: Final[NoiseInstruction] = NoiseInstruction.null_instruction()
CHORD: Final[Dict[ChannelName, InstructionUnion]] = {
    ChannelName.PULSE1: LEAD,
    ChannelName.PULSE2: HARMONY,
    ChannelName.TRIANGLE: BASS,
}
EVERY_PLACE: Final[List[int]] = [0, 1, 2, 3]
WIDE: Final[int] = 64
NARROW: Final[int] = 3
HEAD_AND_SILENCE: Final[int] = 2
ALTERNATE: Final[int] = 1
ONE_ALTERNATE: Final[int] = HEAD_AND_SILENCE + VOLUME_NEIGHBORS + ALTERNATE


@dataclass(frozen=True)
class _Columns:
    """The chord's frame, the winner playing the chord, and the proposals the columns draw on."""

    fragment: Fragment
    layout: StemLayout
    catalogs: Dict[GeneratorClassName, KindCatalog]
    matcher: FrameMatcher
    hearing: SteadyHearing
    winner: ScoredCombination
    proposals: Dict[GeneratorClassName, List[int]]

    def built(self, width: int) -> List[Column]:
        return ChannelColumns(self.fragment, self.layout, self.catalogs, self.matcher, self.hearing, width).columns(
            EVERY_PLACE, self.winner, self.proposals
        )

    def row(self, kind: GeneratorClassName, instruction: InstructionUnion) -> int:
        return self.catalogs[kind].rows_by_instruction[instruction]


def _columns_of(
    fragment: Fragment, all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> _Columns:
    """The columns of ``fragment`` around a winner playing the chord, with the proposals they draw on."""
    layout = separate_layouts(StemsConfig.single_entry(StemSettings.covering(EVERY_CHANNEL)), all_channels)[0]
    catalogs = {
        slot.kind: KindCatalog.build(joint_matcher.candidate_provider, all_channels[slot.channel_name])
        for slot in layout.slots
    }
    hearing = heard_alone(layout, catalogs, joint_matcher.candidate_provider, len(fragment.feature.values))
    weights = np.asarray(to_numpy(joint_matcher.scorer.criterion.weights), dtype=np.float64).reshape(-1)
    judge = CombinationJudge(
        fragment, layout, catalogs, joint_matcher, weights, hearing, StemContinuity.free(layout, catalogs)
    )
    played = [LEAD, HARMONY, BASS, SILENT_NOISE]
    rows = tuple(
        catalogs[slot.kind].rows_by_instruction[instruction] for slot, instruction in zip(layout.slots, played)
    )
    (winner,) = judge.scored([rows])
    proposals = {
        PULSE: [catalogs[PULSE].rows_by_instruction[note] for note in (LEAD, HARMONY, FIRST_OTHER, SECOND_OTHER)],
        TRIANGLE: [catalogs[TRIANGLE].rows_by_instruction[note] for note in (BASS, OTHER_BASS)],
        NOISE: [catalogs[NOISE].rows_by_instruction[HIT]],
    }
    return _Columns(fragment, layout, catalogs, joint_matcher, hearing, winner, proposals)


@pytest.fixture(name="columns", scope="module")
def columns_fixture(
    config: Config,
    extractor: FeatureExtractor,
    all_channels: Dict[ChannelName, GeneratorUnion],
    joint_matcher: FrameMatcher,
) -> _Columns:
    return _columns_of(rendered_fragment(config, extractor, CHORD), all_channels, joint_matcher)


@pytest.fixture(name="louder_columns", scope="module")
def louder_columns_fixture(
    config: Config,
    extractor: FeatureExtractor,
    all_channels: Dict[ChannelName, GeneratorUnion],
    joint_matcher: FrameMatcher,
) -> _Columns:
    """The columns of a frame whose lead plays at full volume, around a winner playing it quieter."""
    louder = {**CHORD, ChannelName.PULSE1: FULL_LEAD}
    return _columns_of(rendered_fragment(config, extractor, louder), all_channels, joint_matcher)


def _instructions(column: Column) -> List[InstructionUnion]:
    return [candidate.instruction for candidate in column]


def _pitches(column: Column) -> List[int]:
    return [
        candidate.instruction.pitch
        for candidate in column
        if isinstance(candidate.instruction, (PulseInstruction, TriangleInstruction)) and candidate.instruction.on
    ]


class TestAChannelsColumn(BaseTestSuite):
    def test_a_pulse_offers_its_note_s_nearest_volumes_and_each_untaken_note_once_and_its_silence(
        self, columns: _Columns
    ) -> None:
        catalog = columns.catalogs[PULSE]
        first, _, _, _ = columns.built(WIDE)

        neighbors = catalog.neighbors(columns.row(PULSE, LEAD), VOLUME_NEIGHBORS)
        own: Set[InstructionUnion] = {
            LEAD,
            *(catalog.instructions[row] for row in neighbors),
            catalog.instructions[catalog.silence],
        }
        offered = _instructions(first)
        others = tuple(candidate for candidate in first if candidate.instruction not in own)
        assert len(neighbors) == VOLUME_NEIGHBORS
        assert own <= set(offered)
        assert sorted(_pitches(others)) == sorted([FIRST_OTHER.pitch, SECOND_OTHER.pitch])

    def test_a_note_the_choice_plays_on_the_other_pulse_is_left_out(self, columns: _Columns) -> None:
        first, second, _, _ = columns.built(WIDE)

        assert HARMONY.pitch not in _pitches(first)
        assert LEAD.pitch not in _pitches(second)

    def test_the_triangle_offers_its_one_level_and_each_untaken_note(self, columns: _Columns) -> None:
        _, _, triangle, _ = columns.built(WIDE)

        assert set(_instructions(triangle)) == {BASS, OTHER_BASS, TriangleInstruction.null_instruction()}

    def test_a_silent_channel_offers_its_silence_and_each_proposed_note(self, columns: _Columns) -> None:
        _, _, _, noise = columns.built(WIDE)

        sounding = [instruction for instruction in _instructions(noise) if instruction.on]
        assert SILENT_NOISE in _instructions(noise)
        assert len(sounding) == 1
        assert isinstance(sounding[0], NoiseInstruction) and sounding[0].period == HIT.period

    def test_a_narrow_column_keeps_the_choice_its_nearest_volume_and_its_silence(self, columns: _Columns) -> None:
        catalog = columns.catalogs[PULSE]
        first, _, _, _ = columns.built(NARROW)

        nearest = catalog.instructions[catalog.neighbors(columns.row(PULSE, LEAD), 1)[0]]
        assert set(_instructions(first)) == {LEAD, nearest, catalog.instructions[catalog.silence]}

    def test_a_narrow_column_is_cut_before_it_is_scored_so_a_farther_volume_waits_however_cheap(
        self, louder_columns: _Columns
    ) -> None:
        """The frame plays the lead at full volume, two steps farther from the winner's than its nearest."""
        catalog = louder_columns.catalogs[PULSE]
        first, _, _, _ = louder_columns.built(NARROW)

        nearest = catalog.instructions[catalog.neighbors(louder_columns.row(PULSE, LEAD), 1)[0]]
        assert set(_instructions(first)) == {LEAD, nearest, catalog.instructions[catalog.silence]}
        assert FULL_LEAD in _instructions(louder_columns.built(WIDE)[0])

    def test_every_column_is_as_wide_as_the_decoder_reads_at_most_and_offers_its_silence(
        self, columns: _Columns
    ) -> None:
        for column in columns.built(NARROW):
            assert len(column) <= NARROW
            assert any(not candidate.instruction.on for candidate in column)

    def test_the_cheapest_untaken_note_comes_first_among_the_alternates(self, columns: _Columns) -> None:
        first, _, _, _ = columns.built(ONE_ALTERNATE)

        kept = [pitch for pitch in _pitches(first) if pitch in (FIRST_OTHER.pitch, SECOND_OTHER.pitch)]
        assert kept == [_cheapest_untaken_note(columns)]

    def test_a_stem_holding_no_channel_has_no_column(self, columns: _Columns) -> None:
        built = ChannelColumns(
            columns.fragment, columns.layout, columns.catalogs, columns.matcher, columns.hearing, WIDE
        ).columns([], columns.winner, columns.proposals)

        assert built == []


def _cheapest_untaken_note(columns: _Columns) -> int:
    """The untaken pulse note whose best row costs least on the first pulse, with the others playing the winner."""
    catalog = columns.catalogs[PULSE]
    mix = FrameMix.empty(columns.fragment)
    for contribution in columns.winner.contributions[1:]:
        if contribution is not None:
            mix = mix.added(contribution)

    best: Dict[int, float] = {}
    for note in (FIRST_OTHER.pitch, SECOND_OTHER.pitch):
        powers = mix.power + columns.hearing.powers(0, catalog.rows_of(note))
        features = columns.matcher.candidate_provider.features_of(xp.asarray(powers))
        best[note] = float(columns.matcher.scorer.spectral_costs(columns.fragment, features).min())

    return min(best, key=best.__getitem__)
