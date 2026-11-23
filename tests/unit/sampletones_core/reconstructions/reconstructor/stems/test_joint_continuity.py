from typing import Dict, Final, List, Mapping, Optional

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights, transition_cost
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.combinations import Rows
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.continuity import (
    ChannelContinuity,
    StemContinuity,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.window.surroundings import ChannelLine
from tests.suite.base import BaseTestSuite

PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
PULSE_AND_NOISE: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.NOISE]
PULSE_AND_TRIANGLE: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
SILENT: Final[PulseInstruction] = PulseInstruction.null_instruction()
BASS: Final[TriangleInstruction] = TriangleInstruction(on=True, pitch=48)
SILENT_BASS: Final[TriangleInstruction] = TriangleInstruction.null_instruction()
HIT: Final[NoiseInstruction] = NoiseInstruction(on=True, period=4, volume=15, short=False)
OTHER_HIT: Final[NoiseInstruction] = NoiseInstruction(on=True, period=8, volume=8, short=False)
WEIGHTS: Final[TransitionWeights] = TransitionWeights(pitch=0.03, volume=0.02, timbre=0.1, on_off=0.2)
INERTIA: Final[float] = 2.0
NO_INERTIA: Final[float] = 0.0
LOUDER_DRIVE: Final[float] = 2.0
FRAMES: Final[int] = 5
CHEAP: Final[float] = 0.1
DEARER: Final[float] = 0.15


@pytest.fixture(name="catalogs", scope="module")
def catalogs_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> Dict[GeneratorClassName, KindCatalog]:
    return {
        generator.class_name(): KindCatalog.build(joint_matcher.candidate_provider, generator)
        for generator in (
            all_channels[ChannelName.PULSE1],
            all_channels[ChannelName.TRIANGLE],
            all_channels[ChannelName.NOISE],
        )
    }


def _layout(all_channels: Dict[ChannelName, GeneratorUnion], channels: List[ChannelName]) -> StemLayout:
    return separate_layouts(StemsConfig.single_entry(StemSettings.covering(channels)), all_channels)[0]


@pytest.fixture(name="pulse_layout", scope="module")
def pulse_layout_fixture(all_channels: Dict[ChannelName, GeneratorUnion]) -> StemLayout:
    return _layout(all_channels, PULSES)


def _line(instructions: List[InstructionUnion]) -> ChannelLine:
    return ChannelLine(
        keys=[None] * len(instructions),
        powers=np.zeros((len(instructions), 1)),
        instructions=list(instructions),
        coherent=True,
    )


def _kept(before: Optional[InstructionUnion], after: Optional[InstructionUnion], inertia: float) -> ChannelContinuity:
    return ChannelContinuity(before=before, after=after, weights=WEIGHTS, inertia=inertia)


def _rows(
    layout: StemLayout, catalogs: Mapping[GeneratorClassName, KindCatalog], instructions: List[InstructionUnion]
) -> Rows:
    return tuple(
        catalogs[slot.kind].rows_by_instruction[instruction] for slot, instruction in zip(layout.slots, instructions)
    )


def _stem(
    layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog], channels: List[Optional[ChannelContinuity]]
) -> StemContinuity:
    return StemContinuity(layout=layout, catalogs=catalogs, channels=tuple(channels))


def _column(instructions: List[InstructionUnion], costs: List[float]) -> Column:
    silence = Contribution.silence(1, 1)
    return tuple(
        ScoredCandidate(instruction=instruction, cost=cost, contribution=silence)
        for instruction, cost in zip(instructions, costs)
    )


class TestAChannelKeptToItsNeighbors(BaseTestSuite):
    def test_playing_what_both_neighbors_play_costs_nothing(self) -> None:
        assert _kept(LEAD, LEAD, INERTIA).charge(LEAD) == 0.0

    def test_a_change_pays_inertia_times_the_decoder_s_charge_on_each_side(self) -> None:
        expected = INERTIA * (transition_cost(LEAD, HARMONY, WEIGHTS) + transition_cost(HARMONY, SILENT, WEIGHTS))

        assert _kept(LEAD, SILENT, INERTIA).charge(HARMONY) == pytest.approx(expected)

    def test_sounding_between_silent_neighbors_pays_both_switches(self) -> None:
        assert _kept(SILENT, SILENT, INERTIA).charge(LEAD) == pytest.approx(INERTIA * 2 * WEIGHTS.on_off)

    def test_a_hole_in_a_held_note_pays_both_switches(self) -> None:
        assert _kept(LEAD, LEAD, INERTIA).charge(SILENT) == pytest.approx(INERTIA * 2 * WEIGHTS.on_off)

    def test_no_inertia_charges_nothing(self) -> None:
        assert _kept(SILENT, SILENT, NO_INERTIA).charge(LEAD) == 0.0

    def test_the_first_frame_answers_to_the_frame_after_it_alone(self) -> None:
        continuity = ChannelContinuity.of(_line([LEAD, SILENT, SILENT]), 0, WEIGHTS, INERTIA)

        assert continuity.before is None
        assert continuity.charge(LEAD) == pytest.approx(INERTIA * WEIGHTS.on_off)

    def test_the_last_frame_answers_to_the_frame_before_it_alone(self) -> None:
        continuity = ChannelContinuity.of(_line([SILENT, LEAD, LEAD]), 2, WEIGHTS, INERTIA)

        assert continuity.after is None
        assert continuity.charge(SILENT) == pytest.approx(INERTIA * WEIGHTS.on_off)

    def test_a_lone_frame_answers_to_no_neighbor(self) -> None:
        continuity = ChannelContinuity.of(_line([LEAD]), 0, WEIGHTS, INERTIA)

        assert continuity.before is None and continuity.after is None
        assert continuity.charge(HARMONY) == 0.0

    @pytest.mark.parametrize("frame", range(FRAMES))
    def test_every_frame_reads_its_neighbors_from_the_line(self, frame: int) -> None:
        line = _line([LEAD, HARMONY, SILENT, LEAD, HARMONY])

        continuity = ChannelContinuity.of(line, frame, WEIGHTS, INERTIA)

        assert continuity.before == (line.instructions[frame - 1] if frame > 0 else None)
        assert continuity.after == (line.instructions[frame + 1] if frame < FRAMES - 1 else None)


class TestAStemKeptToItsNeighbors(BaseTestSuite):
    def test_a_free_stem_charges_nothing_and_holds_nothing(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        free = StemContinuity.free(pulse_layout, catalogs)

        assert not free.binding
        assert free.charge(_rows(pulse_layout, catalogs, [LEAD, HARMONY])) == 0.0
        assert not free.beside()

    def test_a_stem_without_inertia_holds_nothing_and_leaves_its_columns(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        loose = _stem(pulse_layout, catalogs, [_kept(LEAD, LEAD, NO_INERTIA), _kept(HARMONY, HARMONY, NO_INERTIA)])
        column = _column([HARMONY, LEAD], [DEARER, CHEAP])

        assert not loose.binding
        assert not loose.beside()
        assert loose.charged(0, column, _rows(pulse_layout, catalogs, [LEAD, HARMONY])) == column

    def test_a_stem_reads_each_channel_s_continuity_in_layout_order(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        first, second = _kept(LEAD, LEAD, INERTIA), _kept(HARMONY, HARMONY, INERTIA)

        stem = StemContinuity.of(pulse_layout, catalogs, {ChannelName.PULSE2: second, ChannelName.PULSE1: first})

        assert stem.channels == (first, second)

    def test_a_combination_pays_what_its_channels_charges_add_up_to(
        self, all_channels: Dict[ChannelName, GeneratorUnion], catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        layout = _layout(all_channels, PULSE_AND_TRIANGLE)
        lead, bass = _kept(LEAD, LEAD, INERTIA), _kept(SILENT_BASS, SILENT_BASS, INERTIA)
        stem = _stem(layout, catalogs, [lead, bass])

        charge = stem.charge(_rows(layout, catalogs, [HARMONY, BASS]))

        assert charge == pytest.approx(lead.charge(HARMONY) + bass.charge(BASS))

    def test_two_pulses_pay_for_the_order_that_breaks_least(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = _stem(pulse_layout, catalogs, [_kept(LEAD, LEAD, INERTIA), _kept(HARMONY, HARMONY, INERTIA)])

        assert kept.charge(_rows(pulse_layout, catalogs, [HARMONY, LEAD])) == 0.0
        assert kept.charge(_rows(pulse_layout, catalogs, [LEAD, HARMONY])) == 0.0

    def test_pulses_driven_apart_pay_in_their_own_order(
        self, all_channels: Dict[ChannelName, GeneratorUnion], catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        apart = separate_layouts(
            StemsConfig.single_entry(StemSettings.covering(PULSES).with_drive(ChannelName.PULSE2, LOUDER_DRIVE)),
            all_channels,
        )[0]
        first, second = _kept(LEAD, LEAD, INERTIA), _kept(HARMONY, HARMONY, INERTIA)
        kept = _stem(apart, catalogs, [first, second])

        charge = kept.charge(_rows(apart, catalogs, [HARMONY, LEAD]))

        assert charge == pytest.approx(first.charge(HARMONY) + second.charge(LEAD))

    def test_the_noise_without_inertia_pays_nothing_beside_a_kept_pulse(
        self, all_channels: Dict[ChannelName, GeneratorUnion], catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        layout = _layout(all_channels, PULSE_AND_NOISE)
        lead = _kept(LEAD, LEAD, INERTIA)
        stem = _stem(layout, catalogs, [lead, _kept(HIT, HIT, NO_INERTIA)])

        assert stem.binding
        assert stem.charge(_rows(layout, catalogs, [LEAD, OTHER_HIT])) == 0.0
        assert stem.charge(_rows(layout, catalogs, [HARMONY, OTHER_HIT])) == pytest.approx(lead.charge(HARMONY))


class TestTheNeighborsCombinations(BaseTestSuite):
    def test_the_neighbors_combinations_are_offered_before_first(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = _stem(pulse_layout, catalogs, [_kept(LEAD, LEAD, INERTIA), _kept(SILENT, HARMONY, INERTIA)])

        assert kept.beside() == [
            _rows(pulse_layout, catalogs, [LEAD, SILENT]),
            _rows(pulse_layout, catalogs, [LEAD, HARMONY]),
        ]

    def test_neighbors_playing_one_combination_offer_it_once(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = _stem(pulse_layout, catalogs, [_kept(LEAD, LEAD, INERTIA), _kept(HARMONY, HARMONY, INERTIA)])

        assert kept.beside() == [_rows(pulse_layout, catalogs, [LEAD, HARMONY])]

    @pytest.mark.parametrize("first", [True, False], ids=["first-frame", "last-frame"])
    def test_a_frame_at_an_end_offers_its_one_neighbor(
        self, first: bool, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        sides = [(None, LEAD), (None, HARMONY)] if first else [(LEAD, None), (HARMONY, None)]
        kept = _stem(pulse_layout, catalogs, [_kept(before, after, INERTIA) for before, after in sides])

        assert kept.beside() == [_rows(pulse_layout, catalogs, [LEAD, HARMONY])]

    def test_a_lone_frame_offers_no_neighbor(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = _stem(pulse_layout, catalogs, [_kept(None, None, INERTIA), _kept(None, None, INERTIA)])

        assert kept.binding
        assert not kept.beside()


class TestAChargedColumn(BaseTestSuite):
    """A column scores each alternative with the other channels playing the choice, so each pays both charges."""

    def test_an_alternative_pays_its_own_charge_and_the_choice_s_other_channels(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        first, second = _kept(LEAD, LEAD, INERTIA), _kept(SILENT, SILENT, INERTIA)
        kept = _stem(pulse_layout, catalogs, [first, second])
        column = _column([LEAD, HARMONY], [CHEAP, DEARER])

        charged = kept.charged(0, column, _rows(pulse_layout, catalogs, [LEAD, HARMONY]))

        others = second.charge(HARMONY)
        assert [candidate.instruction for candidate in charged] == [LEAD, HARMONY]
        assert [candidate.cost for candidate in charged] == pytest.approx(
            [CHEAP + others + first.charge(LEAD), DEARER + others + first.charge(HARMONY)]
        )

    def test_the_charged_column_comes_cheapest_first(
        self, pulse_layout: StemLayout, catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = _stem(pulse_layout, catalogs, [_kept(HARMONY, HARMONY, INERTIA), _kept(None, None, INERTIA)])
        column = _column([LEAD, HARMONY], [CHEAP, DEARER])

        charged = kept.charged(0, column, _rows(pulse_layout, catalogs, [LEAD, SILENT]))

        assert [candidate.instruction for candidate in charged] == [HARMONY, LEAD]

    def test_the_noise_without_inertia_keeps_its_column_beside_a_kept_pulse(
        self, all_channels: Dict[ChannelName, GeneratorUnion], catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        layout = _layout(all_channels, PULSE_AND_NOISE)
        lead = _kept(LEAD, LEAD, INERTIA)
        stem = _stem(layout, catalogs, [lead, _kept(HIT, HIT, NO_INERTIA)])
        column = _column([OTHER_HIT, HIT], [CHEAP, DEARER])

        charged = stem.charged(1, column, _rows(layout, catalogs, [HARMONY, OTHER_HIT]))

        assert [candidate.instruction for candidate in charged] == [OTHER_HIT, HIT]
        assert [candidate.cost for candidate in charged] == pytest.approx(
            [CHEAP + lead.charge(HARMONY), DEARER + lead.charge(HARMONY)]
        )
