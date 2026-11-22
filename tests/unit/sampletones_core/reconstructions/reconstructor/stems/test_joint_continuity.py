from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstructor.decoder.transition import TransitionWeights
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import KindCatalog
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.continuity import (
    ChannelContinuity,
    StemContinuity,
)
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_core.reconstructions.reconstructor.window.surroundings import ChannelLine

PULSES: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2]
LEAD: Final[PulseInstruction] = PulseInstruction(on=True, pitch=64, volume=12, duty_cycle=2)
HARMONY: Final[PulseInstruction] = PulseInstruction(on=True, pitch=67, volume=8, duty_cycle=1)
SILENT: Final[PulseInstruction] = PulseInstruction.null_instruction()
WEIGHTS: Final[TransitionWeights] = TransitionWeights(pitch=0.03, volume=0.02, timbre=0.1, on_off=0.2)
INERTIA: Final[float] = 2.0
FRAMES: Final[int] = 5


@pytest.fixture(name="pulse_layout", scope="module")
def pulse_layout_fixture(all_channels: Dict[ChannelName, GeneratorUnion]) -> StemLayout:
    return separate_layouts(StemsConfig.single_entry(StemSettings.covering(PULSES)), all_channels)[0]


@pytest.fixture(name="pulse_catalogs", scope="module")
def pulse_catalogs_fixture(
    all_channels: Dict[ChannelName, GeneratorUnion], joint_matcher: FrameMatcher
) -> Dict[GeneratorClassName, KindCatalog]:
    catalog = KindCatalog.build(joint_matcher.candidate_provider, all_channels[ChannelName.PULSE1])
    return {GeneratorClassName.PULSE_GENERATOR: catalog}


def _line(instructions: List[InstructionUnion]) -> ChannelLine:
    return ChannelLine(
        keys=[None] * len(instructions),
        powers=np.zeros((len(instructions), 1)),
        instructions=list(instructions),
        coherent=True,
    )


def _kept(before: InstructionUnion, after: InstructionUnion, inertia: float) -> ChannelContinuity:
    return ChannelContinuity(before=before, after=after, weights=WEIGHTS, inertia=inertia)


def _row(catalogs: Dict[GeneratorClassName, KindCatalog], instruction: PulseInstruction) -> int:
    return catalogs[GeneratorClassName.PULSE_GENERATOR].rows_by_instruction[instruction]


class TestAChannelKeptToItsNeighbors:
    def test_playing_what_both_neighbors_play_costs_nothing(self) -> None:
        assert _kept(LEAD, LEAD, INERTIA).charge(LEAD) == 0.0

    def test_sounding_between_silent_neighbors_pays_both_switches(self) -> None:
        assert _kept(SILENT, SILENT, INERTIA).charge(LEAD) == pytest.approx(INERTIA * 2 * WEIGHTS.on_off)

    def test_a_hole_in_a_held_note_pays_both_switches(self) -> None:
        assert _kept(LEAD, LEAD, INERTIA).charge(SILENT) == pytest.approx(INERTIA * 2 * WEIGHTS.on_off)

    def test_no_inertia_charges_nothing(self) -> None:
        assert _kept(SILENT, SILENT, 0.0).charge(LEAD) == 0.0

    def test_the_first_frame_answers_to_the_frame_after_it_alone(self) -> None:
        continuity = ChannelContinuity.of(_line([LEAD, SILENT, SILENT]), 0, WEIGHTS, INERTIA)

        assert continuity.before is None
        assert continuity.charge(LEAD) == pytest.approx(INERTIA * WEIGHTS.on_off)

    def test_the_last_frame_answers_to_the_frame_before_it_alone(self) -> None:
        continuity = ChannelContinuity.of(_line([SILENT, LEAD, LEAD]), 2, WEIGHTS, INERTIA)

        assert continuity.after is None
        assert continuity.charge(SILENT) == pytest.approx(INERTIA * WEIGHTS.on_off)


class TestAStemKeptToItsNeighbors:
    def test_a_free_stem_charges_nothing_and_holds_nothing(
        self, pulse_layout: StemLayout, pulse_catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        free = StemContinuity.free(pulse_layout)
        rows = (_row(pulse_catalogs, LEAD), _row(pulse_catalogs, HARMONY))

        assert free.charge(pulse_layout, pulse_catalogs, rows) == 0.0
        assert not free.beside(pulse_layout, pulse_catalogs)

    def test_two_pulses_pay_for_the_order_that_breaks_least(
        self, pulse_layout: StemLayout, pulse_catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = StemContinuity(channels=(_kept(LEAD, LEAD, INERTIA), _kept(HARMONY, HARMONY, INERTIA)))
        swapped = (_row(pulse_catalogs, HARMONY), _row(pulse_catalogs, LEAD))

        assert kept.charge(pulse_layout, pulse_catalogs, swapped) == 0.0

    def test_the_neighbors_combinations_are_offered_once_each(
        self, pulse_layout: StemLayout, pulse_catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        kept = StemContinuity(channels=(_kept(LEAD, LEAD, INERTIA), _kept(SILENT, HARMONY, INERTIA)))

        beside = kept.beside(pulse_layout, pulse_catalogs)

        assert beside == [
            (_row(pulse_catalogs, LEAD), _row(pulse_catalogs, SILENT)),
            (_row(pulse_catalogs, LEAD), _row(pulse_catalogs, HARMONY)),
        ]

    def test_a_stem_without_inertia_holds_nothing(
        self, pulse_layout: StemLayout, pulse_catalogs: Dict[GeneratorClassName, KindCatalog]
    ) -> None:
        loose = StemContinuity(channels=(_kept(LEAD, LEAD, 0.0), _kept(HARMONY, HARMONY, 0.0)))

        assert not loose.binding
        assert not loose.beside(pulse_layout, pulse_catalogs)


@pytest.mark.parametrize("frame", range(FRAMES))
def test_every_frame_reads_its_neighbors_from_the_line(frame: int) -> None:
    line = _line([LEAD, HARMONY, SILENT, LEAD, HARMONY])

    continuity = ChannelContinuity.of(line, frame, WEIGHTS, INERTIA)

    assert continuity.before == (line.instructions[frame - 1] if frame > 0 else None)
    assert continuity.after == (line.instructions[frame + 1] if frame < FRAMES - 1 else None)
