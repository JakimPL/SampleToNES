from typing import Dict

import pytest

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import (
    FULL_VOLUME,
    NOISE_MODES,
    KindCatalog,
    note_of,
)


@pytest.fixture(name="pulses", scope="module")
def pulses_fixture(joint_matcher: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]) -> KindCatalog:
    return KindCatalog.build(joint_matcher.candidate_provider, all_channels[ChannelName.PULSE1])


def _row(catalog: KindCatalog, volume: int) -> int:
    return catalog.instructions.index(PulseInstruction(on=True, pitch=64, volume=volume, duty_cycle=2))


class TestKindCatalog:
    def test_a_note_s_rows_sound_that_note_in_every_timbre_and_volume(self, pulses: KindCatalog) -> None:
        rows = pulses.rows_of(64)

        assert {pulses.instructions[row].pitch for row in rows} == {64}
        assert {int(pulses.timbres[row]) for row in rows} == {1, 2}

    def test_the_loudest_row_of_a_note_plays_it_at_full_volume(self, pulses: KindCatalog) -> None:
        assert pulses.volumes[pulses.loudest(64, 2)] == FULL_VOLUME

    @pytest.mark.parametrize("volume, expected", [(10.6, 11), (13.6, 15), (4.2, 4)], ids=["eleven", "fifteen", "four"])
    def test_a_fitted_volume_lands_on_the_nearest_row_the_library_holds(
        self, pulses: KindCatalog, volume: float, expected: int
    ) -> None:
        assert pulses.volumes[pulses.nearest(_row(pulses, 15), volume)] == expected

    def test_a_fitted_volume_under_half_a_step_is_silence(self, pulses: KindCatalog) -> None:
        assert pulses.nearest(_row(pulses, 15), 0.3) == pulses.silence

    def test_a_row_s_neighbors_are_the_nearest_volumes_of_its_note_and_timbre(self, pulses: KindCatalog) -> None:
        neighbors = pulses.neighbors(_row(pulses, 11), 2)

        assert [int(pulses.volumes[row]) for row in neighbors] == [12, 8]
        assert {int(pulses.timbres[row]) for row in neighbors} == {2}

    def test_the_silent_row_sounds_no_note(self, pulses: KindCatalog) -> None:
        assert not pulses.sounding(pulses.silence)
        assert pulses.note_name(pulses.silence) is None


class TestNoteOf:
    def test_a_noise_note_is_its_period_with_its_mode(self) -> None:
        assert note_of(NoiseInstruction(on=True, period=4, volume=8, short=True)) == NOISE_MODES * 4 + 1

    def test_the_triangle_s_note_is_its_pitch(self) -> None:
        assert note_of(TriangleInstruction(on=True, pitch=48)) == 48

    def test_a_kind_reads_as_its_generator_class(self, pulses: KindCatalog) -> None:
        assert pulses.kind == GeneratorClassName.PULSE_GENERATOR
