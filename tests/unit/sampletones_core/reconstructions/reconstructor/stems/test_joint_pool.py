from dataclasses import replace
from typing import Dict, Final, List, Mapping, Optional, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_FRAME_COST
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.base import PooledCombination
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.choice import ScoredCombination
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.pool import resting_pool, sounding_pool
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool
from tests.suite.base import BaseTestSuite

from ..conftest import rendered_fragment

CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
OTHER: Final[PulseInstruction] = PulseInstruction(on=True, pitch=60, volume=12, duty_cycle=2)
SILENT: Final[PulseInstruction] = PulseInstruction.null_instruction()
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
SILENT_BASS: Final[TriangleInstruction] = TriangleInstruction.null_instruction()
CHOICE_COST: Final[float] = 0.5
CHOICE_CHARGE: Final[float] = 0.1
OTHER_COST: Final[float] = 0.55
MOVE_COST: Final[float] = 0.7
FURTHER_MOVE_COST: Final[float] = 0.8
LOUDER_DRIVE: Final[float] = 2.0

Played = Tuple[InstructionUnion, ...]


@pytest.fixture(name="catalogs", scope="module")
def catalogs_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> Dict[GeneratorClassName, KindCatalog]:
    return {
        generator.class_name(): KindCatalog.build(joint_matcher.candidate_provider, generator)
        for generator in (all_channels[ChannelName.PULSE1], all_channels[ChannelName.TRIANGLE])
    }


@pytest.fixture(name="layout", scope="module")
def layout_fixture(all_channels: Dict[ChannelName, GeneratorUnion]) -> StemLayout:
    return separate_layouts(StemsConfig.single_entry(StemSettings.covering(CHANNELS)), all_channels)[0]


@pytest.fixture(name="fragment", scope="module")
def fragment_fixture(config: Config, extractor: FeatureExtractor) -> Fragment:
    return rendered_fragment(config, extractor, {ChannelName.PULSE1: LEAD, ChannelName.PULSE2: HARMONY})


def _sound(fragment: Fragment) -> Contribution:
    """A contribution standing for what a sounding channel adds, told apart from others by identity."""
    return Contribution.silence(len(fragment.feature.values), fragment.audio.shape[0])


def _scored(
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    layout: StemLayout,
    played: List[InstructionUnion],
    contributions: List[Optional[Contribution]],
    cost: float,
    charge: float,
) -> ScoredCombination:
    return ScoredCombination(
        rows=tuple(
            catalogs[slot.kind].rows_by_instruction[instruction] for slot, instruction in zip(layout.slots, played)
        ),
        cost=cost,
        contributions=tuple(contributions),
        charge=charge,
    )


def _column(fragment: Fragment, instructions: List[InstructionUnion], costs: List[float]) -> Column:
    return tuple(
        ScoredCandidate(instruction=instruction, cost=cost, contribution=_sound(fragment))
        for instruction, cost in zip(instructions, costs)
    )


def _played(combination: PooledCombination) -> Played:
    return tuple(candidate.instruction for candidate in combination.candidates)


def _by_played(pool: StemPool) -> Dict[Played, PooledCombination]:
    return {_played(combination): combination for combination in pool.combinations}


class TestASoundingPool(BaseTestSuite):
    @pytest.fixture(name="choice")
    def choice_fixture(
        self, fragment: Fragment, catalogs: Dict[GeneratorClassName, KindCatalog], layout: StemLayout
    ) -> ScoredCombination:
        return _scored(
            catalogs,
            layout,
            [LEAD, HARMONY, SILENT_BASS],
            [_sound(fragment), _sound(fragment), None],
            CHOICE_COST,
            CHOICE_CHARGE,
        )

    def test_the_choice_comes_first_every_channel_at_what_the_choice_weighs(
        self,
        fragment: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        layout: StemLayout,
        choice: ScoredCombination,
    ) -> None:
        pool = sounding_pool(fragment, layout, [choice], {}, catalogs)

        first = pool.combinations[0]
        assert _played(first) == (LEAD, HARMONY, SILENT_BASS)
        assert first.cost == pytest.approx(CHOICE_COST + CHOICE_CHARGE)
        assert {candidate.cost for candidate in first.candidates} == {first.cost}
        assert pool.channel_names == tuple(CHANNELS)

    def test_a_channel_keeps_what_it_adds_and_a_silent_one_adds_the_frame_s_silence(
        self,
        fragment: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        layout: StemLayout,
        choice: ScoredCombination,
    ) -> None:
        first = sounding_pool(fragment, layout, [choice], {}, catalogs).combinations[0]

        assert first.candidates[0].contribution is choice.contributions[0]
        silence = first.candidates[2].contribution
        assert not silence.sounding
        assert np.array_equal(silence.power, np.zeros(len(fragment.feature.values)))
        assert np.array_equal(silence.expectation, np.zeros(fragment.audio.shape[0]))

    def test_each_alternative_of_each_column_moves_the_choice_one_channel_at_the_column_s_cost(
        self,
        fragment: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        layout: StemLayout,
        choice: ScoredCombination,
    ) -> None:
        columns = {
            0: _column(fragment, [OTHER, SILENT], [MOVE_COST, FURTHER_MOVE_COST]),
            2: _column(fragment, [BASS], [MOVE_COST]),
        }

        pooled = _by_played(sounding_pool(fragment, layout, [choice], columns, catalogs))

        for played, cost in [
            ((OTHER, HARMONY, SILENT_BASS), MOVE_COST),
            ((SILENT, HARMONY, SILENT_BASS), FURTHER_MOVE_COST),
            ((LEAD, HARMONY, BASS), MOVE_COST),
        ]:
            moved = pooled[played]
            assert moved.cost == cost
            assert {candidate.cost for candidate in moved.candidates} == {cost}

        assert pooled[(OTHER, HARMONY, SILENT_BASS)].candidates[1].contribution is choice.contributions[1]
        assert pooled[(OTHER, HARMONY, SILENT_BASS)].candidates[0].contribution is columns[0][0].contribution

    def test_every_combination_stands_in_both_orders_of_pulses_driven_alike(
        self,
        fragment: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        layout: StemLayout,
        choice: ScoredCombination,
    ) -> None:
        columns = {0: _column(fragment, [OTHER], [MOVE_COST])}

        pooled = _by_played(sounding_pool(fragment, layout, [choice], columns, catalogs))

        assert pooled[(HARMONY, LEAD, SILENT_BASS)].cost == pooled[(LEAD, HARMONY, SILENT_BASS)].cost
        assert pooled[(HARMONY, OTHER, SILENT_BASS)].cost == MOVE_COST
        assert len(pooled) == 4

    def test_pulses_driven_apart_stand_in_their_own_order(
        self,
        fragment: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        all_channels: Dict[ChannelName, GeneratorUnion],
        choice: ScoredCombination,
    ) -> None:
        settings = StemSettings.covering(CHANNELS).with_drive(ChannelName.PULSE2, LOUDER_DRIVE)
        apart = separate_layouts(StemsConfig.single_entry(settings), all_channels)[0]

        pool = sounding_pool(fragment, apart, [choice], {}, catalogs)

        assert [_played(combination) for combination in pool.combinations] == [(LEAD, HARMONY, SILENT_BASS)]

    def test_a_combination_reads_once_at_the_cost_it_was_first_pooled_with(
        self,
        fragment: Fragment,
        catalogs: Dict[GeneratorClassName, KindCatalog],
        layout: StemLayout,
        choice: ScoredCombination,
    ) -> None:
        swapped = replace(choice, rows=(choice.rows[1], choice.rows[0], choice.rows[2]), cost=OTHER_COST, charge=0.0)
        other = _scored(
            catalogs, layout, [OTHER, HARMONY, SILENT_BASS], [_sound(fragment), _sound(fragment), None], OTHER_COST, 0.0
        )
        columns = {0: _column(fragment, [OTHER], [MOVE_COST])}

        pool = sounding_pool(fragment, layout, [choice, swapped, other], columns, catalogs)

        pooled = _by_played(pool)
        assert pooled[(HARMONY, LEAD, SILENT_BASS)].cost == pytest.approx(CHOICE_COST + CHOICE_CHARGE)
        assert pooled[(OTHER, HARMONY, SILENT_BASS)].cost == OTHER_COST
        assert len(pool.combinations) == len(pooled) == 4


class TestARestingPool(BaseTestSuite):
    def test_a_silent_frame_pools_every_channel_resting_at_the_resting_cost(
        self, fragment: Fragment, layout: StemLayout, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        pool = resting_pool(fragment, layout, all_channels)

        (resting,) = pool.combinations
        assert pool.channel_names == tuple(CHANNELS)
        assert resting.cost == RESTING_FRAME_COST
        assert _played(resting) == (SILENT, SILENT, SILENT_BASS)
        assert {candidate.cost for candidate in resting.candidates} == {RESTING_FRAME_COST}
