from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME, MIN_PITCH, MIN_PLAYED_PITCH
from sampletones_core.exporters.skipped import SkippedRow, SkipReason
from sampletones_core.formats.famitracker.builder import (
    build_instrument_table,
    build_module,
    project_to_module,
)
from sampletones_core.formats.famitracker.model.module import FamiTrackerModule
from sampletones_core.formats.famitracker.model.pattern import RowCell
from sampletones_core.formats.famitracker.specification.channels import (
    CHANNEL_COUNT_2A03,
    ChannelId,
)
from sampletones_core.formats.famitracker.specification.instruments import (
    MAX_INSTRUMENTS,
)
from sampletones_core.formats.famitracker.specification.parameters import (
    ENGINE_SPEED_MACHINE_DEFAULT,
    EXPANSION_NONE,
    Machine,
)
from sampletones_core.formats.famitracker.specification.patterns import (
    EMPTY_EFFECT,
    EMPTY_EFFECT_PARAM,
    EMPTY_INSTRUMENT,
    EMPTY_VOLUME,
    NoteValue,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    NO_LOOP_POINT,
    SequenceKind,
)
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.performance.modifiers import triangle_sounds_at
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import voice_reference
from sampletones_core.structures import IdentifiedCollection
from sampletones_core.utils.frequencies import transpose_pitch
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.famitracker import FAMITRACKER_OPENING_VOLUME, cell_pitch, column_volume
from tests.suite.performance import song_row_volumes

from .conftest import (
    RECONSTRUCTION_LENGTH,
    ProjectFixture,
    build_reconstruction,
    contour_sample,
    pulse_sample,
    triangle_sample,
)

LEAD_PITCH = 60
OCTAVE = 12
CUSTOM_NES_FREQUENCY = 30

ROWS_PER_PATTERN: Final[int] = 8
BASS_PITCH: Final[int] = 48
TRANSPOSE: Final[int] = 5
QUIET_VOLUME: Final[int] = 4
NOTE_OFF_VOLUME: Final[int] = 6
CLOSING_VOLUME: Final[int] = 9
FRAME_CLOSING_VOLUME: Final[int] = 2
QUIET_TRIANGLE_VOLUME: Final[int] = 5
LOUD_TRIANGLE_VOLUME: Final[int] = 12
RESTING_TRIANGLE_VOLUME: Final[int] = 7
NOTE_TRIANGLE_VOLUME: Final[int] = 3
SILENT_COLUMN: Final[int] = 0
PLAYED_PASSES: Final[int] = 2
LOW_PITCH: Final[int] = 36
LOW_TRANSPOSE: Final[int] = -10
CONTOUR_PITCHES: Final[Tuple[int, ...]] = (40, 50)
SUBMERGED_TRANSPOSE: Final[int] = -20


class TestBuildInstrumentTable:
    def test_one_instrument_per_generator_slice(self, project_fixture: ProjectFixture) -> None:
        instruments, slots = build_instrument_table(project_fixture.project)
        # lead (pulse) + pad (pulse) + drum (noise) + bell (pulse + triangle) = 5
        assert len(instruments) == 5

    def test_slot_maps_sample_and_generator_to_index(self, project_fixture: ProjectFixture) -> None:
        _, slots = build_instrument_table(project_fixture.project)
        assert slots[(project_fixture.lead.id, ChannelName.PULSE1)].index == 0
        assert slots[(project_fixture.bell.id, ChannelName.TRIANGLE)].index == 4

    def test_slot_carries_initial_pitch(self, project_fixture: ProjectFixture) -> None:
        _, slots = build_instrument_table(project_fixture.project)
        assert slots[(project_fixture.lead.id, ChannelName.PULSE1)].initial_pitch == LEAD_PITCH

    def test_slot_keeps_its_pitch_after_an_arpeggio_edit(self, project_fixture: ProjectFixture) -> None:
        """A pattern row triggers the instrument at the note its sample was reconstructed at.

        Raising a channel's first frame an octave moves the arpeggio sequence, and the row
        keeps naming the reference pitch — so the tracker plays the contour the reconstruction
        view sounds.
        """
        arpeggiated = [
            PulseInstruction(on=True, pitch=LEAD_PITCH + OCTAVE, volume=15, duty_cycle=0),
            PulseInstruction(on=True, pitch=LEAD_PITCH, volume=8, duty_cycle=0),
        ]
        project_fixture.lead.reconstruction = project_fixture.lead.reconstruction.with_channel_data(
            ChannelName.PULSE1,
            arpeggiated,
            LEAD_PITCH,
            (),
            heard=project_fixture.lead.reconstruction.recorded_stem_ids,
        )

        instruments, slots = build_instrument_table(project_fixture.project)

        slot = slots[(project_fixture.lead.id, ChannelName.PULSE1)]
        assert slot.initial_pitch == LEAD_PITCH
        assert list(instruments[slot.index].sequences[SequenceKind.ARPEGGIO].items)[0] == OCTAVE

    def test_a_recordings_sequences_state_no_loop_point(self, project_fixture: ProjectFixture) -> None:
        """A recording is the fixed run of frames its conversion found, so nothing in it circles."""
        instruments, slots = build_instrument_table(project_fixture.project)
        indices = [slots[(voice.id, ChannelName.PULSE1)].index for voice in (project_fixture.lead, project_fixture.pad)]

        points = [instruments[index].sequences[SequenceKind.VOLUME].loop_point for index in indices]

        assert points == [NO_LOOP_POINT, NO_LOOP_POINT]

    def test_exceeding_max_instruments_raises(self) -> None:
        project = Project.create()
        for number in range(MAX_INSTRUMENTS + 1):
            instructions = [PulseInstruction(on=True, pitch=60, volume=15, duty_cycle=0)]
            reconstruction = build_reconstruction({ChannelName.PULSE1: instructions})
            project.voices.append(Sample(name=f"sample-{number}", reconstruction=reconstruction))
        with pytest.raises(ValueError):
            build_instrument_table(project)


class TestProjectToModuleParameters:
    def test_expansion_and_channel_count(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert module.parameters.expansion_chip == EXPANSION_NONE
        assert module.parameters.channel_count == CHANNEL_COUNT_2A03

    def test_machine_and_engine_speed_from_default_frequency(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert module.parameters.machine == Machine.NTSC
        assert module.parameters.engine_speed == ENGINE_SPEED_MACHINE_DEFAULT

    def test_machine_and_engine_speed_from_a_custom_frequency(self, project_fixture: ProjectFixture) -> None:
        project_fixture.project.settings.nes_frequency = CUSTOM_NES_FREQUENCY

        module = project_to_module(project_fixture.project)

        assert module.parameters.machine == Machine.NTSC
        assert module.parameters.engine_speed == CUSTOM_NES_FREQUENCY

    def test_information_and_comment_carry_through(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert module.information.title == "Demo"
        assert module.information.author == "Tester"
        assert module.comment == "a comment"

    def test_track_timing_from_settings(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        settings = project_fixture.project.settings
        assert module.track.speed == settings.speed
        assert module.track.tempo == settings.tempo
        assert module.track.rows_per_pattern == project_fixture.project.song.rows_per_pattern


class TestProjectToModulePatterns:
    def _pattern(self, module_patterns, channel: ChannelId, index: int):
        return next(p for p in module_patterns if p.channel == channel and p.index == index)

    def test_only_non_empty_patterns_emitted(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        channels = {pattern.channel for pattern in module.track.patterns}
        assert channels == {ChannelId.SQUARE1, ChannelId.NOISE}

    def test_instrument_row_resolves_note_and_volume(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        first = next(row for row in pattern.rows if row.row_number == 0)
        # initial_pitch 60 + transpose 0 -> C-3 (note 1, octave 3)
        assert first.note == 1
        assert first.octave == 3
        assert first.instrument == 0
        assert first.volume == 10

    def test_note_off_becomes_halt(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        halt = next(row for row in pattern.rows if row.row_number == 2)
        assert halt.note == int(NoteValue.HALT)
        assert halt.instrument == EMPTY_INSTRUMENT

    def test_volume_only_row_keeps_empty_note_and_instrument(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        volume_only = next(row for row in pattern.rows if row.row_number == 4)
        assert volume_only.note == int(NoteValue.NONE)
        assert volume_only.instrument == EMPTY_INSTRUMENT
        assert volume_only.volume == 5

    def test_empty_rows_are_dropped(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.SQUARE1, 0)
        assert {row.row_number for row in pattern.rows} == {0, 2, 4}

    def test_every_row_leaves_its_effect_columns_empty(self, project_fixture: ProjectFixture) -> None:
        """A `Vxx` is what moves FamiTracker's default duty, so every note there starts on duty 0."""
        module = project_to_module(project_fixture.project)
        effects = {effect for pattern in module.track.patterns for row in pattern.rows for effect in row.effects}
        assert effects == {(EMPTY_EFFECT, EMPTY_EFFECT_PARAM)}

    def test_noise_row_uses_period_note(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        pattern = self._pattern(module.track.patterns, ChannelId.NOISE, 0)
        first = next(row for row in pattern.rows if row.row_number == 0)
        # period 4 -> note 5, octave 0
        assert first.note == 5
        assert first.octave == 0


class TestARowWithNoInstrumentOnItsChannel:
    """A voice sounds on the channels its instruments cover, so a row naming it elsewhere plays
    nothing in the song. The export writes a note cut there and reports the row."""

    DRUM_ROW = 3

    def _with_drum_on_pulse2(self, project_fixture: ProjectFixture) -> None:
        rows = [Row() for _ in range(8)]
        rows[self.DRUM_ROW] = Row(command=NoteOn(voice_id=project_fixture.drum.id), volume=9)
        song = project_fixture.project.song
        song.channels[ChannelName.PULSE2] = Channel(name=ChannelName.PULSE2, patterns={0: Pattern(rows=rows)})
        song.order[0][ChannelName.PULSE2] = 0

    def test_the_row_is_written_as_a_note_cut(self, project_fixture: ProjectFixture) -> None:
        self._with_drum_on_pulse2(project_fixture)

        module = project_to_module(project_fixture.project)

        pattern = next(
            pattern for pattern in module.track.patterns if pattern.channel == ChannelId.SQUARE2 and pattern.index == 0
        )
        cut = next(row for row in pattern.rows if row.row_number == self.DRUM_ROW)
        assert cut.note == int(NoteValue.HALT)
        assert cut.instrument == EMPTY_INSTRUMENT
        assert cut.volume == 9

    def test_the_row_is_reported_where_the_tracker_shows_it(self, project_fixture: ProjectFixture) -> None:
        self._with_drum_on_pulse2(project_fixture)

        skipped = build_module(project_fixture.project).skipped_rows

        assert skipped == (
            SkippedRow(
                voice_id=project_fixture.drum.id,
                channel=ChannelName.PULSE2,
                order_position=0,
                row_index=self.DRUM_ROW,
                reason=SkipReason.NO_INSTRUMENT,
            ),
        )

    def test_a_pattern_the_order_plays_twice_reports_each_frame(self, project_fixture: ProjectFixture) -> None:
        self._with_drum_on_pulse2(project_fixture)
        project_fixture.project.song.order[1][ChannelName.PULSE2] = 0

        skipped = build_module(project_fixture.project).skipped_rows

        assert [row.order_position for row in skipped] == [0, 1]

    def test_a_pattern_no_frame_plays_reports_nothing(self, project_fixture: ProjectFixture) -> None:
        self._with_drum_on_pulse2(project_fixture)
        project_fixture.project.song.order[0][ChannelName.PULSE2] = None

        assert build_module(project_fixture.project).skipped_rows == ()

    def test_a_project_naming_only_voices_with_instruments_reports_nothing(
        self,
        project_fixture: ProjectFixture,
    ) -> None:
        assert build_module(project_fixture.project).skipped_rows == ()


class TestProjectToModuleOrder:
    def test_order_has_one_entry_per_channel(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert len(module.track.order) == 2
        assert all(len(frame) == CHANNEL_COUNT_2A03 for frame in module.track.order)

    def test_referenced_patterns_appear_in_order(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        first_frame = module.track.order[0]
        assert first_frame[ChannelId.SQUARE1] == 0
        assert first_frame[ChannelId.NOISE] == 0

    def test_none_slots_map_to_a_reserved_pattern_index(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        second_frame = module.track.order[1]
        # every None slot resolves to a concrete uint8 index
        assert all(isinstance(index, int) and index >= 0 for index in second_frame)

    def test_dpcm_channel_is_always_empty(self, project_fixture: ProjectFixture) -> None:
        module = project_to_module(project_fixture.project)
        assert all(frame[ChannelId.DPCM] == 0 for frame in module.track.order)


def rows_with(*cells: Tuple[int, Row]) -> List[Row]:
    """A pattern's rows, blank apart from the ones given by their index."""
    rows = [Row() for _ in range(ROWS_PER_PATTERN)]
    for row_index, row in cells:
        rows[row_index] = row

    return rows


def arranged_project(
    voices: Sequence[Sample],
    patterns: Mapping[ChannelName, Mapping[int, List[Row]]],
    order: List[Dict[ChannelName, Optional[int]]],
) -> Project:
    """A project playing ``voices`` through the channel patterns ``order`` names."""
    pool: IdentifiedCollection[Sample] = IdentifiedCollection()
    for voice in voices:
        pool.append(voice)

    channels = {
        channel_name: Channel(
            name=channel_name,
            patterns={index: Pattern(rows=rows) for index, rows in patterns.get(channel_name, {}).items()},
        )
        for channel_name in ChannelName.items()
    }
    project = Project.create(title="Rows", author="Tester", settings=ProjectSettings())
    project.voices = pool
    project.song = Song(rows_per_pattern=ROWS_PER_PATTERN, order=order, channels=channels)
    return project


def played_volumes(module: FamiTrackerModule, channel: ChannelId) -> List[int]:
    """The level FamiTracker plays one channel at on each row, the order played through and round again.

    FamiTracker wraps from the last frame to the first, keeping every channel's level, so a second
    pass shows what the level the song ends on does to the notes it opens with.
    """
    cells = {
        (pattern.channel, pattern.index): {row.row_number: row for row in pattern.rows}
        for pattern in module.track.patterns
    }
    level = FAMITRACKER_OPENING_VOLUME
    levels: List[int] = []
    for _ in range(PLAYED_PASSES):
        for frame in module.track.order:
            pattern = cells.get((channel, frame[int(channel)]), {})
            for row_number in range(module.track.rows_per_pattern):
                cell = pattern.get(row_number)
                if cell is not None:
                    level = column_volume(level, cell.volume)

                levels.append(level)

    return levels


def pattern_cell(module: FamiTrackerModule, channel: ChannelId, index: int, row_number: int) -> RowCell:
    pattern = next(
        pattern for pattern in module.track.patterns if pattern.channel == channel and pattern.index == index
    )
    return next(row for row in pattern.rows if row.row_number == row_number)


@pytest.fixture(name="lead")
def lead_fixture() -> Sample:
    return pulse_sample("lead", pitch=LEAD_PITCH)


@pytest.fixture(name="bass")
def bass_fixture() -> Sample:
    return triangle_sample("bass", pitch=BASS_PITCH)


class TestTheLevelsAPlayedModuleCarries:
    """The song starts a note stating no level at the full level and sounds the triangle only above
    half volume, while FamiTracker carries the last level a cell wrote into every note and sounds the
    triangle at any level above silence. The module therefore writes its volume column so that
    FamiTracker, playing the order through and round again, plays each row the song sounds at the
    song's own level, including in a pattern two frames reach at different levels.
    """

    @pytest.fixture(name="arranged")
    def arranged_fixture(self, lead: Sample, bass: Sample) -> Project:
        lead_note = Row(command=NoteOn(voice_id=lead.id))
        bass_note = Row(command=NoteOn(voice_id=bass.id))
        pulse = {
            0: rows_with(
                (0, lead_note),
                (1, Row(volume=QUIET_VOLUME)),
                (2, Row(pitch=Step(value=TRANSPOSE))),
                (3, lead_note),
                (4, Row(command=NoteOff(), volume=NOTE_OFF_VOLUME)),
                (5, lead_note),
                (6, Row(volume=CLOSING_VOLUME)),
            ),
            1: rows_with(
                (0, lead_note),
                (3, Row(volume=FRAME_CLOSING_VOLUME)),
            ),
        }
        triangle = {
            0: rows_with(
                (0, bass_note),
                (2, Row(volume=QUIET_TRIANGLE_VOLUME)),
                (4, Row(volume=LOUD_TRIANGLE_VOLUME)),
                (6, bass_note),
            ),
            1: rows_with(
                (0, Row(volume=RESTING_TRIANGLE_VOLUME)),
                (2, bass_note),
                (5, Row(command=NoteOn(voice_id=bass.id), volume=NOTE_TRIANGLE_VOLUME)),
            ),
        }
        order: List[Dict[ChannelName, Optional[int]]] = [
            {ChannelName.PULSE1: 0, ChannelName.TRIANGLE: 0},
            {ChannelName.PULSE1: 1, ChannelName.TRIANGLE: 1},
            {ChannelName.PULSE1: None, ChannelName.TRIANGLE: 0},
            {ChannelName.PULSE1: 0, ChannelName.TRIANGLE: None},
        ]
        return arranged_project(
            (lead, bass),
            {ChannelName.PULSE1: pulse, ChannelName.TRIANGLE: triangle},
            order,
        )

    def test_the_pulse_plays_every_sounding_row_at_the_song_level(self, arranged: Project) -> None:
        played = played_volumes(project_to_module(arranged), ChannelId.SQUARE1)
        song = song_row_volumes(arranged, ChannelName.PULSE1) * PLAYED_PASSES

        sounding = [(level, volume) for level, volume in zip(played, song) if volume is not None]
        assert [level for level, _ in sounding] == [volume for _, volume in sounding]

    def test_the_triangle_sounds_on_every_row_the_song_sounds_it(self, arranged: Project) -> None:
        played = played_volumes(project_to_module(arranged), ChannelId.TRIANGLE)
        song = song_row_volumes(arranged, ChannelName.TRIANGLE) * PLAYED_PASSES

        sounding = [(level, volume) for level, volume in zip(played, song) if volume is not None]
        assert [level > 0 for level, _ in sounding] == [triangle_sounds_at(volume) for _, volume in sounding]

    def test_a_note_after_a_quieter_row_starts_at_the_full_level(self, arranged: Project) -> None:
        cell = pattern_cell(project_to_module(arranged), ChannelId.SQUARE1, 0, 3)
        assert cell.volume == MAX_VOLUME

    def test_a_note_the_channel_reaches_at_the_full_level_leaves_the_column_alone(self, lead: Sample) -> None:
        lead_note = Row(command=NoteOn(voice_id=lead.id))
        project = arranged_project(
            (lead,),
            {ChannelName.PULSE1: {0: rows_with((0, lead_note), (4, lead_note))}},
            [{ChannelName.PULSE1: 0}, {ChannelName.PULSE1: 0}],
        )

        module = project_to_module(project)

        assert [pattern_cell(module, ChannelId.SQUARE1, 0, row).volume for row in (0, 4)] == [EMPTY_VOLUME] * 2

    def test_a_pattern_one_frame_reaches_quieter_writes_the_full_level(self, arranged: Project) -> None:
        """The module stores the pulse's first pattern once for the two frames that play it, and the
        second of them reaches its opening note at the level the frame before it ends on.
        """
        cell = pattern_cell(project_to_module(arranged), ChannelId.SQUARE1, 0, 0)
        assert cell.volume == MAX_VOLUME


class TestTheTriangleSoundsAboveHalfVolume(BaseTestSuite):
    """The song sounds the triangle while a row asks for more than half volume, while FamiTracker
    sounds it at any column level above zero, so a quieter row writes the level that silences it.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        volume: int
        expected: int

    test_cases: Tuple["TestTheTriangleSoundsAboveHalfVolume.TestCase", ...] = (
        TestCase(label="a level the triangle rests at", volume=QUIET_TRIANGLE_VOLUME, expected=SILENT_COLUMN),
        TestCase(label="a level the triangle sounds at", volume=LOUD_TRIANGLE_VOLUME, expected=LOUD_TRIANGLE_VOLUME),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_row_writes_the_triangle_gate(
        self,
        bass: Sample,
        test_case: "TestTheTriangleSoundsAboveHalfVolume.TestCase",
    ) -> None:
        project = arranged_project(
            (bass,),
            {ChannelName.TRIANGLE: {0: rows_with((0, Row(command=NoteOn(voice_id=bass.id), volume=test_case.volume)))}},
            [{ChannelName.TRIANGLE: 0}],
        )

        assert pattern_cell(project_to_module(project), ChannelId.TRIANGLE, 0, 0).volume == test_case.expected


class TestALowTransposeKeepsTheSongsPitch:
    """The song and FamiTracker both hold every tick's transposed pitch within C-0..B-7, and both play a
    note below A-0 at the longest period. FamiTracker writes no note below C-0, so a transpose below it
    writes C-0.
    """

    @staticmethod
    def _transposed(sample: Sample, transpose: int) -> Tuple[FamiTrackerModule, RowCell]:
        project = arranged_project(
            (sample,),
            {
                ChannelName.PULSE1: {
                    0: rows_with((0, Row(command=NoteOn(voice_id=sample.id), pitch=Step(value=transpose))))
                }
            },
            [{ChannelName.PULSE1: 0}],
        )
        module = project_to_module(project)
        return (
            module,
            pattern_cell(module, ChannelId.SQUARE1, 0, 0),
        )

    @staticmethod
    def _arpeggio(module: FamiTrackerModule) -> Tuple[int, ...]:
        return module.instruments[0].sequences[SequenceKind.ARPEGGIO].items

    def test_a_flat_voice_transposed_below_a0_writes_its_own_note(self) -> None:
        _, cell = self._transposed(pulse_sample("low", pitch=LOW_PITCH), LOW_TRANSPOSE)

        assert cell_pitch(cell) == LOW_PITCH + LOW_TRANSPOSE < MIN_PITCH

    def test_a_flat_voice_transposed_below_c0_writes_c0(self) -> None:
        _, cell = self._transposed(pulse_sample("low", pitch=LOW_PITCH), SUBMERGED_TRANSPOSE)

        assert cell_pitch(cell) == MIN_PLAYED_PITCH

    def test_a_contour_reaching_below_c0_plays_every_tick_where_the_song_does(self) -> None:
        sample = contour_sample("contour", CONTOUR_PITCHES)
        reference = voice_reference(sample, ChannelName.PULSE1)
        transpose = MIN_PLAYED_PITCH + 1 - reference
        module, cell = self._transposed(sample, transpose)

        steps = self._arpeggio(module)
        tracker = [transpose_pitch(cell_pitch(cell), step) for step in steps]
        song = [transpose_pitch(reference + step, transpose) for step in steps]

        assert cell_pitch(cell) == reference + transpose
        assert min(song) == MIN_PLAYED_PITCH
        assert tracker == song
