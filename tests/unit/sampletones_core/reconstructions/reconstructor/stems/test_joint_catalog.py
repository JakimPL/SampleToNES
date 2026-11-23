from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import MAX_VOLUME, MIN_VOLUME
from sampletones_core.fft import Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library import InstructionLibraryData, InstructionLibraryFragment
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.catalog import (
    NO_TIMBRE,
    NOISE_MODES,
    SILENT_NOTE,
    SILENT_VOLUME,
    KindCatalog,
    RowSound,
    UnitRow,
    alike_timbres,
)
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..conftest import JOINT_DUTY_CYCLES, JOINT_PULSE_PITCHES, JOINT_PULSE_VOLUMES, JOINT_SIGNAL_LENGTH

PITCH: Final[int] = 64
DUTY_CYCLE: Final[int] = 2
QUIETEST: Final[int] = min(JOINT_PULSE_VOLUMES)
LOUDEST: Final[int] = max(JOINT_PULSE_VOLUMES)
UNIT_VOLUME: Final[int] = 6
POWER_TOLERANCE: Final[float] = 1e-3


def _pulse(volume: int, duty_cycle: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=PITCH, volume=volume, duty_cycle=duty_cycle)


@pytest.fixture(name="pulses", scope="module")
def pulses_fixture(joint_matcher: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]) -> KindCatalog:
    """The pulse rows of the joint library: a few notes in two duty cycles at a spread of volumes."""
    return KindCatalog.build(joint_matcher.candidate_provider, all_channels[ChannelName.PULSE1])


def _row(catalog: KindCatalog, volume: int, duty_cycle: int) -> int:
    return catalog.rows_by_instruction[_pulse(volume, duty_cycle)]


class TestARowSound(BaseTestSuite):
    """A row sounds a note, a timbre within it and a volume, whatever its kind."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        instruction: InstructionUnion
        expected: RowSound

    test_cases = (
        TestCase(
            label="pulse",
            instruction=PulseInstruction(on=True, pitch=PITCH, volume=9, duty_cycle=3),
            expected=RowSound(note=PITCH, timbre=3, volume=9),
        ),
        TestCase(
            label="triangle_at_full_volume",
            instruction=TriangleInstruction(on=True, pitch=48),
            expected=RowSound(note=48, timbre=NO_TIMBRE, volume=MAX_VOLUME),
        ),
        TestCase(
            label="long_noise",
            instruction=NoiseInstruction(on=True, period=4, volume=8, short=False),
            expected=RowSound(note=NOISE_MODES * 4, timbre=NO_TIMBRE, volume=8),
        ),
        TestCase(
            label="short_noise",
            instruction=NoiseInstruction(on=True, period=4, volume=8, short=True),
            expected=RowSound(note=NOISE_MODES * 4 + 1, timbre=NO_TIMBRE, volume=8),
        ),
        TestCase(
            label="silent_pulse",
            instruction=PulseInstruction.null_instruction(),
            expected=RowSound(note=SILENT_NOTE, timbre=NO_TIMBRE, volume=SILENT_VOLUME),
        ),
        TestCase(
            label="silent_noise",
            instruction=NoiseInstruction.null_instruction(),
            expected=RowSound(note=SILENT_NOTE, timbre=NO_TIMBRE, volume=SILENT_VOLUME),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_row_reads_as_its_note_timbre_and_volume(self, test_case: TestCase) -> None:
        assert RowSound.of(test_case.instruction) == test_case.expected


class TestAUnitRow(BaseTestSuite):
    """A level scales a unit row's power, and a row's power grows with its volume squared."""

    def test_a_row_at_the_unit_s_volume_sounds_level_one_and_half_as_loud_a_quarter(self) -> None:
        unit = UnitRow(row=0, volume=UNIT_VOLUME)

        assert unit.level_of(UNIT_VOLUME) == 1.0
        assert unit.level_of(UNIT_VOLUME // 2) == pytest.approx(0.25)

    def test_full_volume_is_the_level_of_the_loudest_volume(self) -> None:
        assert UnitRow(row=0, volume=UNIT_VOLUME).full_level == pytest.approx((MAX_VOLUME / UNIT_VOLUME) ** 2)
        assert UnitRow(row=0, volume=MAX_VOLUME).full_level == 1.0

    @pytest.mark.parametrize("volume", [1, UNIT_VOLUME, MAX_VOLUME], ids=["quietest", "unit", "full"])
    def test_a_level_sounds_back_the_volume_it_was_read_from(self, volume: int) -> None:
        unit = UnitRow(row=0, volume=UNIT_VOLUME)

        assert unit.volume_at(unit.level_of(volume)) == pytest.approx(volume)

    @pytest.mark.parametrize("level", [0.0, -1e-12], ids=["zero", "under_zero"])
    def test_a_level_of_zero_or_under_sounds_no_volume(self, level: float) -> None:
        assert UnitRow(row=0, volume=UNIT_VOLUME).volume_at(level) == 0.0


class TestKindCatalog(BaseTestSuite):
    """A kind's rows grouped by note and timbre, which the search moves along to change a level or a timbre."""

    def test_a_note_s_rows_sound_that_note_in_every_timbre_and_volume(self, pulses: KindCatalog) -> None:
        rows = pulses.rows_of(PITCH)

        assert {pulses.instructions[row].pitch for row in rows} == {PITCH}
        assert {int(pulses.timbres[row]) for row in rows} == set(JOINT_DUTY_CYCLES)

    def test_the_rows_like_a_row_are_its_note_in_its_timbre_at_every_volume(self, pulses: KindCatalog) -> None:
        rows = pulses.rows_like(_row(pulses, 8, DUTY_CYCLE))

        assert {pulses.instructions[row] for row in rows} == {
            _pulse(volume, DUTY_CYCLE) for volume in JOINT_PULSE_VOLUMES
        }

    def test_the_sounded_notes_are_ascending_and_leave_out_silence(self, pulses: KindCatalog) -> None:
        assert pulses.sounded_notes == sorted(JOINT_PULSE_PITCHES)

    def test_the_loudest_row_of_a_note_plays_it_at_full_volume(self, pulses: KindCatalog) -> None:
        assert pulses.volumes[pulses.loudest(PITCH, DUTY_CYCLE)] == MAX_VOLUME

    def test_a_note_and_timbre_the_catalog_lacks_has_no_loudest_row(self, pulses: KindCatalog) -> None:
        with pytest.raises(ValueError, match="sounds note"):
            pulses.loudest(PITCH, max(JOINT_DUTY_CYCLES) + 1)

    def test_a_row_s_unit_is_the_loudest_of_its_note_and_timbre(self, pulses: KindCatalog) -> None:
        unit = pulses.unit_of(_row(pulses, QUIETEST, DUTY_CYCLE))

        assert unit == UnitRow(row=_row(pulses, LOUDEST, DUTY_CYCLE), volume=LOUDEST)

    @pytest.mark.parametrize("volume", sorted(JOINT_PULSE_VOLUMES), ids=lambda volume: f"volume_{volume}")
    def test_a_row_sounds_the_share_of_its_unit_s_power_its_level_reads(self, pulses: KindCatalog, volume: int) -> None:
        """A row's power grows with the square of its volume, which every level against a unit assumes."""
        row = _row(pulses, volume, DUTY_CYCLE)
        unit = pulses.unit_of(row)

        share = float(pulses.powers[row].sum() / pulses.powers[unit.row].sum())

        assert share == pytest.approx(unit.level_of(volume), rel=POWER_TOLERANCE)

    def test_a_note_has_one_unit_in_each_timbre_in_timbre_order(self, pulses: KindCatalog) -> None:
        units = pulses.units_of(PITCH)

        assert [unit.row for unit in units] == [
            _row(pulses, LOUDEST, duty_cycle) for duty_cycle in sorted(JOINT_DUTY_CYCLES)
        ]

    def test_a_row_s_volume_reads_at_least_the_quietest_a_sounding_row_plays(self, pulses: KindCatalog) -> None:
        assert pulses.sounding_volume(_row(pulses, 8, DUTY_CYCLE)) == 8
        assert pulses.sounding_volume(pulses.silence) == MIN_VOLUME

    @pytest.mark.parametrize(
        "volume, expected",
        [(10.6, 11), (13.6, 15), (4.2, 4), (0.5, QUIETEST), (2 * MAX_VOLUME, LOUDEST)],
        ids=["eleven", "fifteen", "four", "half_a_step", "past_full_volume"],
    )
    def test_a_fitted_volume_lands_on_the_nearest_row_the_library_holds(
        self, pulses: KindCatalog, volume: float, expected: int
    ) -> None:
        assert pulses.volumes[pulses.nearest(_row(pulses, LOUDEST, DUTY_CYCLE), volume)] == expected

    def test_a_fitted_volume_under_half_a_step_is_silence(self, pulses: KindCatalog) -> None:
        assert pulses.nearest(_row(pulses, LOUDEST, DUTY_CYCLE), 0.49) == pulses.silence

    def test_a_volume_equally_near_two_rows_lands_on_the_one_the_catalog_holds_first(self, pulses: KindCatalog) -> None:
        """The catalog holds a note's quieter rows first, so the quieter one answers."""
        nearest = pulses.nearest(_row(pulses, LOUDEST, DUTY_CYCLE), (4 + 8) / 2)

        assert pulses.volumes[nearest] == 4

    def test_a_row_s_neighbors_are_the_nearest_volumes_of_its_note_and_timbre(self, pulses: KindCatalog) -> None:
        neighbors = pulses.neighbors(_row(pulses, 11, DUTY_CYCLE), 2)

        assert [int(pulses.volumes[row]) for row in neighbors] == [12, 8]
        assert {int(pulses.timbres[row]) for row in neighbors} == {DUTY_CYCLE}

    def test_equally_near_neighbors_keep_their_catalog_order(self, pulses: KindCatalog) -> None:
        """Volume 8 lies four steps from both 4 and 12, and the catalog holds 4 first."""
        neighbors = pulses.neighbors(_row(pulses, 8, DUTY_CYCLE), 3)

        assert [int(pulses.volumes[row]) for row in neighbors] == [11, 4, 12]

    def test_a_row_has_at_most_its_note_s_other_volumes_as_neighbors(self, pulses: KindCatalog) -> None:
        neighbors = pulses.neighbors(_row(pulses, 8, DUTY_CYCLE), 2 * len(JOINT_PULSE_VOLUMES))

        assert len(neighbors) == len(JOINT_PULSE_VOLUMES) - 1

    def test_the_silent_row_sounds_no_note(self, pulses: KindCatalog) -> None:
        assert not pulses.sounding(pulses.silence)
        assert pulses.note_name(pulses.silence) is None
        assert pulses.key(pulses.silence) is None

    def test_a_sounding_row_s_key_is_its_note_and_timbre(self, pulses: KindCatalog) -> None:
        assert pulses.key(_row(pulses, 8, DUTY_CYCLE)) == (PITCH, DUTY_CYCLE)
        assert pulses.note_name(_row(pulses, 8, DUTY_CYCLE)) == PITCH

    def test_a_kind_reads_as_its_generator_class(self, pulses: KindCatalog) -> None:
        assert pulses.kind == GeneratorClassName.PULSE_GENERATOR


@pytest.fixture(name="silenceless_matcher", scope="module")
def silenceless_matcher_fixture(config: Config, window: Window, extractor: FeatureExtractor) -> FrameMatcher:
    """The matcher of a library holding two pulse notes and no silent pulse."""
    channels = get_generators_by_channels(config, [ChannelName.PULSE1])
    generator = channels[ChannelName.PULSE1]
    data: Dict[InstructionUnion, InstructionLibraryFragment[Any]] = {
        instruction: InstructionLibraryFragment.create(generator, instruction, extractor)
        for instruction in (_pulse(LOUDEST, DUTY_CYCLE), _pulse(QUIETEST, DUTY_CYCLE))
    }
    return ReconstructorWorker(
        config=config,
        window=window,
        channels=channels,
        library_data=InstructionLibraryData.create(config, data),
        signal_length=JOINT_SIGNAL_LENGTH,
    ).matcher


class TestBuildingACatalog(BaseTestSuite):
    def test_a_library_lacking_a_kind_s_silence_is_refused(
        self, silenceless_matcher: FrameMatcher, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        with pytest.raises(ValueError, match="silent instruction"):
            KindCatalog.build(silenceless_matcher.candidate_provider, all_channels[ChannelName.PULSE1])


class TestAlikeTimbres(BaseTestSuite):
    @pytest.mark.parametrize("timbre", [1, 3], ids=["quarter", "three_quarters"])
    def test_the_quarter_and_three_quarter_duty_cycles_sound_alike(self, timbre: int) -> None:
        assert alike_timbres(timbre) == {1, 3}

    @pytest.mark.parametrize("timbre", [0, 2], ids=["eighth", "half"])
    def test_another_duty_cycle_sounds_alike_to_itself_alone(self, timbre: int) -> None:
        assert alike_timbres(timbre) == {timbre}
