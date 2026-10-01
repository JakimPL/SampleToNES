from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_core.constants.enums import (
    DEFAULT_CHANNELS,
    ChannelName,
)
from sampletones_core.constants.general import MIN_PITCH, SILENT_VOLUME
from sampletones_core.exporters.skipped import SkippedRow, SkipReason
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.bitphase.builder import build_bitphase, project_to_bitphase
from sampletones_core.formats.bitphase.model.pattern import BitphaseRow, EffectCell, NoteCell
from sampletones_core.formats.bitphase.model.project import BitphaseProject
from sampletones_core.formats.bitphase.notes import (
    note_index_to_note_cell,
    pitch_to_note_index,
)
from sampletones_core.formats.bitphase.specification.channels import ChannelIndex
from sampletones_core.formats.bitphase.specification.chip import DEFAULT_A4_TUNING, DEFAULT_CPU_FREQUENCY
from sampletones_core.formats.bitphase.specification.effects import (
    NO_EFFECT_TABLE,
    SPEED_EFFECT_DELAY,
    EffectId,
)
from sampletones_core.formats.bitphase.specification.patterns import (
    FIRST_OCTAVE,
    FULL_VOLUME,
    MAX_NOTE_INDEX,
    MIN_NOTE_INDEX,
    NO_INSTRUMENT_CHANGE,
    NO_TABLE_CHANGE,
    NO_VOLUME_CHANGE,
    NOTE_INDEX_PITCH_OFFSET,
    NOTE_RANGE,
    SYMBOL_BASE,
    TABLE_COLUMN_OFFSET,
    VOLUME_OFF,
    NoteName,
)
from sampletones_core.formats.bitphase.tuning import DEFAULT_TUNING_TABLE, generate_tuning_table
from sampletones_core.instructions.implementation.pulse import PulseInstruction
from sampletones_core.instructions.implementation.triangle import TriangleInstruction
from sampletones_core.instructions.instruction import Instruction
from sampletones_core.performance.modifiers import triangle_sounds_at
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.song import Song
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceUnion, voice_reference
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.structures import IdentifiedCollection
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from sampletones_core.utils.frequencies import transpose_pitch
from tests.suite.base import BaseTestSuite
from tests.suite.bitphase import BITPHASE_OPENING_PATTERN_VOLUME, pattern_volume
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import song_row_volumes
from tests.suite.stems import single_entry_stems_data

RECONSTRUCTION_LENGTH: Final[int] = 4
ROWS_PER_PATTERN: Final[int] = 8
LEAD_PITCH: Final[int] = 60
BASS_PITCH: Final[int] = 36
TRANSPOSE: Final[int] = 5
ROW_VOLUME: Final[int] = 10
TRIGGER_ROW: Final[int] = 0
NOTE_OFF_ROW: Final[int] = 2
TRANSPOSED_ROW: Final[int] = 4
EMPTY_ROW: Final[int] = 6
SILENCED_ROW: Final[int] = 7
GROOVE_TEMPO: Final[int] = 210
GROOVE_TICKS: Final[Tuple[int, ...]] = (5, 4, 4, 4, 5, 4, 4, 4)
RETUNED_A4_FREQUENCY: Final[float] = 432.0
QUIET_VOLUME: Final[int] = 4
NOTE_OFF_VOLUME: Final[int] = 6
CLOSING_VOLUME: Final[int] = 9
FRAME_CLOSING_VOLUME: Final[int] = 2
QUIET_TRIANGLE_VOLUME: Final[int] = 5
LOUD_TRIANGLE_VOLUME: Final[int] = 12
RESTING_TRIANGLE_VOLUME: Final[int] = 7
NOTE_TRIANGLE_VOLUME: Final[int] = 3
PLAYED_PASSES: Final[int] = 2
LOW_PITCH: Final[int] = 36
LOW_TRANSPOSE: Final[int] = -10
CONTOUR_PITCHES: Final[Tuple[int, ...]] = (40, 50)
STRADDLING_TRANSPOSE: Final[int] = -14
SUBMERGED_TRANSPOSE: Final[int] = -20


def build_reconstruction(
    instructions: Mapping[ChannelName, Sequence[Instruction]],
    *,
    config: Config,
) -> Reconstruction:
    approximations = {channel: np.zeros(RECONSTRUCTION_LENGTH, dtype=np.float32) for channel in instructions}
    return Reconstruction.create(
        instructions=instructions,
        config=config,
        coefficient=1.0,
        audio_filepath=(Path("/dev/null"),),
        stems_data=single_entry_stems_data(list(DEFAULT_CHANNELS), instructions),
    )


def pulse_sample(
    name: str,
    pitch: int,
    *,
    config: Config,
) -> Sample:
    instructions = [PulseInstruction(on=True, pitch=pitch, volume=15, duty_cycle=0)]
    return Sample(
        name=name,
        reconstruction=build_reconstruction(
            {ChannelName.PULSE1: instructions},
            config=config,
        ),
    )


def contour_sample(
    name: str,
    pitches: Sequence[int],
    *,
    config: Config,
) -> Sample:
    """A pulse sample sounding each pitch for one frame, so its table moves the note between them."""
    instructions = [PulseInstruction(on=True, pitch=pitch, volume=15, duty_cycle=0) for pitch in pitches]
    return Sample(
        name=name,
        reconstruction=build_reconstruction(
            {ChannelName.PULSE1: instructions},
            config=config,
        ),
    )


def triangle_sample(
    name: str,
    pitch: int,
    *,
    config: Config,
) -> Sample:
    instructions = [TriangleInstruction(on=True, pitch=pitch)]
    return Sample(
        name=name,
        reconstruction=build_reconstruction(
            {ChannelName.TRIANGLE: instructions},
            config=config,
        ),
    )


@pytest.fixture(name="lead")
def lead_fixture() -> Sample:
    return pulse_sample("Lead", LEAD_PITCH, config=Config())


@pytest.fixture(name="bass")
def bass_fixture() -> Sample:
    return triangle_sample("Bass", BASS_PITCH, config=Config())


@pytest.fixture(name="source")
def source_fixture(lead: Sample, bass: Sample) -> Project:
    voices: IdentifiedCollection[Sample] = IdentifiedCollection()
    for sample in (lead, bass):
        voices.append(sample)

    pulse_rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
    pulse_rows[TRIGGER_ROW] = Row(
        command=NoteOn(voice_id=lead.id),
        transpose=0,
        volume=ROW_VOLUME,
    )
    pulse_rows[NOTE_OFF_ROW] = Row(command=NoteOff())
    pulse_rows[TRANSPOSED_ROW] = Row(
        command=NoteOn(voice_id=lead.id),
        transpose=TRANSPOSE,
    )
    pulse_rows[SILENCED_ROW] = Row(volume=SILENT_VOLUME)

    triangle_rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
    triangle_rows[TRIGGER_ROW] = Row(
        command=NoteOn(voice_id=bass.id),
        transpose=0,
    )

    channels = {
        ChannelName.PULSE1: Channel(name=ChannelName.PULSE1, patterns={0: Pattern(rows=pulse_rows)}),
        ChannelName.PULSE2: Channel(name=ChannelName.PULSE2, patterns={}),
        ChannelName.TRIANGLE: Channel(name=ChannelName.TRIANGLE, patterns={0: Pattern(rows=triangle_rows)}),
        ChannelName.NOISE: Channel(name=ChannelName.NOISE, patterns={}),
    }
    order: List[Dict[ChannelName, Optional[int]]] = [
        {ChannelName.PULSE1: 0, ChannelName.TRIANGLE: 0},
        {ChannelName.PULSE1: None, ChannelName.TRIANGLE: 0},
    ]

    project = Project.create(title="Demo", author="Tester", settings=ProjectSettings())
    project.voices = voices
    project.song = Song(rows_per_pattern=ROWS_PER_PATTERN, order=order, channels=channels)
    return project


@pytest.fixture(name="document")
def document_fixture(source: Project) -> BitphaseProject:
    return project_to_bitphase(source)


@pytest.fixture(name="grooved_document")
def grooved_document_fixture(source: Project) -> BitphaseProject:
    """The same project at a tempo whose row rate falls between two whole tick counts."""
    source.settings.tempo = GROOVE_TEMPO
    return project_to_bitphase(source)


def groove_channel_rows(document: BitphaseProject, pattern_index: int) -> Tuple[BitphaseRow, ...]:
    """The lines of the channel the groove rides, within one pattern."""
    return document.songs[0].patterns[pattern_index].channels[int(ChannelIndex.DPCM)].rows


class TestTheDocumentCarriesTheProject:
    def test_the_title_and_author_cross_over(self, document: BitphaseProject, source: Project) -> None:
        assert (document.name, document.author) == (
            source.info.title,
            source.info.author,
        )

    def test_the_speed_and_tick_rate_cross_over(self, document: BitphaseProject, source: Project) -> None:
        song = document.songs[0]
        assert song.initial_speed == source.settings.speed
        assert song.interrupt_frequency == source.settings.nes_frequency

    def test_every_sample_slice_becomes_an_instrument(self, document: BitphaseProject) -> None:
        assert [instrument.name for instrument in document.instruments] == [
            "Lead (pulse1)",
            "Bass (triangle)",
        ]


class TestTheOrderFlattens:
    """A SampleToNES order frame points each channel at its own pattern, where a Bitphase
    order position names one pattern spanning every channel, so each frame becomes a
    pattern of its own carrying that frame's channels side by side.
    """

    def test_each_order_frame_becomes_one_pattern(self, document: BitphaseProject, source: Project) -> None:
        assert len(document.songs[0].patterns) == len(source.song.order)

    def test_the_order_plays_those_patterns_in_turn(self, document: BitphaseProject, source: Project) -> None:
        assert document.pattern_order == tuple(range(len(source.song.order)))

    def test_a_frame_carries_the_channels_it_names(self, document: BitphaseProject) -> None:
        pattern = document.songs[0].patterns[0]
        triggered = {
            index
            for index, channel in enumerate(pattern.channels)
            if any(row.instrument != NO_INSTRUMENT_CHANGE for row in channel.rows)
        }
        assert triggered == {int(ChannelIndex.SQUARE1), int(ChannelIndex.TRIANGLE)}

    def test_a_channel_the_frame_leaves_unset_stays_empty(self, document: BitphaseProject) -> None:
        pattern = document.songs[0].patterns[1]
        rows = pattern.channels[int(ChannelIndex.SQUARE1)].rows
        assert all(row.instrument == NO_INSTRUMENT_CHANGE for row in rows)

    def test_every_pattern_is_as_long_as_the_song_declares(self, document: BitphaseProject, source: Project) -> None:
        patterns = document.songs[0].patterns
        assert all(pattern.length == source.song.rows_per_pattern for pattern in patterns)


class TestRowCells:
    def test_a_trigger_names_its_instrument_and_table(self, document: BitphaseProject) -> None:
        """Bitphase matches the instrument column against ``parseInt(id, 36)``, so the
        column and the instrument's own identifier name the same voice.
        """
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRIGGER_ROW]
        assert row.instrument == int(document.instruments[0].id, SYMBOL_BASE)
        assert row.table == document.tables[0].id + TABLE_COLUMN_OFFSET

    def test_a_trigger_plays_the_pitch_the_slice_was_reconstructed_at(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRIGGER_ROW]
        assert row.note == note_index_to_note_cell(pitch_to_note_index(LEAD_PITCH))

    def test_a_transposed_trigger_moves_that_pitch(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRANSPOSED_ROW]
        assert row.note == note_index_to_note_cell(pitch_to_note_index(LEAD_PITCH + TRANSPOSE))

    def test_a_row_volume_reaches_the_volume_column(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRIGGER_ROW]
        assert row.volume == ROW_VOLUME

    def test_a_note_after_a_quieter_row_starts_at_the_full_level(self, document: BitphaseProject) -> None:
        """The song starts a note stating no level at the full level, while Bitphase carries the
        level the trigger row set into it, so the note writes the full level.
        """
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[TRANSPOSED_ROW]
        assert row.volume == FULL_VOLUME

    def test_a_note_the_channel_reaches_at_the_full_level_leaves_the_column_alone(
        self,
        document: BitphaseProject,
    ) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.TRIANGLE)].rows[TRIGGER_ROW]
        assert row.volume == NO_VOLUME_CHANGE

    def test_a_row_asking_for_silence_silences_the_channel(self, document: BitphaseProject) -> None:
        """Bitphase reads a stored volume of ``0`` as "carry the level forward", so silence
        is the value below it — the one its editor prints as the digit ``0`` — and a row
        asking for silence has to reach a different column than a row asking for nothing.
        """
        rows = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows
        assert rows[SILENCED_ROW].volume == VOLUME_OFF
        assert rows[SILENCED_ROW].volume != rows[TRANSPOSED_ROW].volume

    def test_a_note_off_stops_the_channel(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[NOTE_OFF_ROW]
        assert row.note.name == int(NoteName.OFF)
        assert row.instrument == NO_INSTRUMENT_CHANGE

    def test_a_blank_line_leaves_every_column_alone(self, document: BitphaseProject) -> None:
        row = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[EMPTY_ROW]
        assert row.note.name == int(NoteName.NONE)
        assert (row.instrument, row.table, row.volume) == (
            NO_INSTRUMENT_CHANGE,
            NO_TABLE_CHANGE,
            NO_VOLUME_CHANGE,
        )


def played_speeds(document: BitphaseProject) -> List[Tuple[int, ...]]:
    """The ticks each row of every pattern lasts, the order played once through.

    The song starts at its initial speed, and a speed effect sets the speed from its row on.
    """
    song = document.songs[0]
    patterns = {pattern.id: pattern for pattern in song.patterns}
    speed = song.initial_speed
    played: List[Tuple[int, ...]] = []
    for pattern_id in document.pattern_order:
        pattern = patterns[pattern_id]
        rows: List[int] = []
        for row_index in range(pattern.length):
            for channel in pattern.channels:
                for effect in channel.rows[row_index].effects:
                    if effect is not None and effect.effect == int(EffectId.SPEED):
                        speed = effect.parameter

            rows.append(speed)

        played.append(tuple(rows))

    return played


class TestTheTempoBecomesSpeeds:
    """A Bitphase song holds one speed value per row, so the fractional row rate most tempi ask for
    is carried by speed effects that change it where the rows' lengths change. They ride the channel
    this exporter leaves silent. A tempo whose rows all last alike is carried by the song's initial
    speed alone.
    """

    def test_the_document_holds_one_table_per_slice(
        self,
        document: BitphaseProject,
        grooved_document: BitphaseProject,
    ) -> None:
        assert len(document.tables) == len(document.instruments)
        assert len(grooved_document.tables) == len(grooved_document.instruments)

    def test_a_tempo_the_speed_column_states_leaves_the_speed_channel_resting(
        self,
        document: BitphaseProject,
    ) -> None:
        for pattern_index in range(len(document.songs[0].patterns)):
            assert all(row == BitphaseRow() for row in groove_channel_rows(document, pattern_index))

    def test_the_song_starts_on_the_ticks_its_first_row_lasts(self, grooved_document: BitphaseProject) -> None:
        assert grooved_document.songs[0].initial_speed == GROOVE_TICKS[TRIGGER_ROW]

    def test_every_row_plays_the_ticks_the_songs_timing_gives_it(
        self,
        grooved_document: BitphaseProject,
        source: Project,
    ) -> None:
        """At tempo 210 an 8-row pattern lasts 34 2/7 ticks, so the second frame plays one tick more."""
        timing = SongTiming.from_project(source, bounds=SONG_TICK_BOUNDS)
        expected = [timing.groove(frame).ticks for frame in range(source.song.order_length())]

        assert played_speeds(grooved_document) == expected
        assert expected[0] == GROOVE_TICKS
        assert sum(expected[1]) == sum(GROOVE_TICKS) + 1

    def test_a_speed_is_stated_only_where_a_row_lasts_differently_from_the_row_before(
        self,
        grooved_document: BitphaseProject,
    ) -> None:
        """The song comes round to its first row after the last, so that is the row before the first."""
        speeds = [speed for pattern in played_speeds(grooved_document) for speed in pattern]
        changes = sum(1 for index, speed in enumerate(speeds) if speed != speeds[index - 1])
        stated = sum(
            1
            for pattern_index in range(len(grooved_document.songs[0].patterns))
            for row in groove_channel_rows(grooved_document, pattern_index)
            if row != BitphaseRow()
        )

        assert stated == changes

    def test_the_speed_channel_carries_nothing_but_speeds(self, grooved_document: BitphaseProject) -> None:
        speeds = {GROOVE_TICKS[TRIGGER_ROW], *GROOVE_TICKS}
        for pattern_index in range(len(grooved_document.songs[0].patterns)):
            for row in groove_channel_rows(grooved_document, pattern_index):
                if row == BitphaseRow():
                    continue

                (effect,) = row.effects
                assert effect is not None
                assert (effect.effect, effect.delay, effect.table_index) == (
                    int(EffectId.SPEED),
                    SPEED_EFFECT_DELAY,
                    NO_EFFECT_TABLE,
                )
                assert effect.parameter in speeds

    def test_the_sounding_channels_keep_their_effect_columns(self, grooved_document: BitphaseProject) -> None:
        """The speeds ride the silent channel, so every channel that plays keeps the one
        effect column the chip gives it.
        """
        channels = grooved_document.songs[0].patterns[0].channels[: int(ChannelIndex.DPCM)]
        assert all(row.effects == (None,) for channel in channels for row in channel.rows)


class TestARowWithNoInstrumentOnItsChannel:
    """A voice sounds on the channels its instruments cover, so a row naming it elsewhere plays
    nothing in the song. The export writes a note cut there and reports the row."""

    @staticmethod
    def _with_lead_on_pulse2(source: Project, lead: Sample) -> None:
        rows: List[Row] = [Row() for _ in range(ROWS_PER_PATTERN)]
        rows[TRIGGER_ROW] = Row(command=NoteOn(voice_id=lead.id), volume=ROW_VOLUME)
        source.song.channels[ChannelName.PULSE2] = Channel(
            name=ChannelName.PULSE2,
            patterns={0: Pattern(rows=rows)},
        )
        source.song.order[0][ChannelName.PULSE2] = 0

    def test_the_row_is_written_as_a_note_cut(self, source: Project, lead: Sample) -> None:
        self._with_lead_on_pulse2(source, lead)

        document = project_to_bitphase(source)

        cut = document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE2)].rows[TRIGGER_ROW]
        assert cut.note is not None
        assert cut.note.name == int(NoteName.OFF)
        assert cut.volume == ROW_VOLUME

    def test_the_row_is_reported_where_the_tracker_shows_it(self, source: Project, lead: Sample) -> None:
        self._with_lead_on_pulse2(source, lead)

        skipped = build_bitphase(source).skipped_rows

        assert skipped == (
            SkippedRow(
                voice_id=lead.id,
                channel=ChannelName.PULSE2,
                order_position=0,
                row_index=TRIGGER_ROW,
                reason=SkipReason.NO_INSTRUMENT,
            ),
        )

    def test_a_pattern_the_order_plays_twice_reports_each_frame(self, source: Project, lead: Sample) -> None:
        self._with_lead_on_pulse2(source, lead)
        source.song.order[1][ChannelName.PULSE2] = 0

        skipped = build_bitphase(source).skipped_rows

        assert [row.order_position for row in skipped] == [0, 1]

    def test_a_project_naming_only_voices_with_instruments_reports_nothing(self, source: Project) -> None:
        assert build_bitphase(source).skipped_rows == ()


class TestAProjectSoundsItsSamplesTuning:
    """A song plays at one tuning, and a project's samples state it by agreeing on it, so the song
    takes the tuning they were reconstructed at.
    """

    @pytest.fixture(name="retuned_config")
    def retuned_config_fixture(self) -> Config:
        return Config(library=InstructionsLibraryConfig(a4_frequency=RETUNED_A4_FREQUENCY))

    @pytest.fixture(name="lead")
    def lead_fixture(self, retuned_config: Config) -> Sample:
        return pulse_sample("Lead", LEAD_PITCH, config=retuned_config)

    @pytest.fixture(name="bass")
    def bass_fixture(self, retuned_config: Config) -> Sample:
        return triangle_sample("Bass", BASS_PITCH, config=retuned_config)

    def test_the_song_takes_the_tuning_its_samples_share(self, document: BitphaseProject) -> None:
        song = document.songs[0]
        assert song.a4_tuning_hz == RETUNED_A4_FREQUENCY
        assert song.tuning_table == generate_tuning_table(DEFAULT_CPU_FREQUENCY, a4_tuning=RETUNED_A4_FREQUENCY)

    def test_samples_reconstructed_at_different_tunings_are_refused(self, source: Project) -> None:
        """One table sounds one tuning, so a project whose samples disagree has no song to write."""
        source.voices.append(triangle_sample("Concert bass", BASS_PITCH, config=Config()))
        with pytest.raises(ValueError, match=str(RETUNED_A4_FREQUENCY)):
            build_bitphase(source)

    def test_a_project_of_instruments_alone_plays_at_concert_pitch(self) -> None:
        voices: IdentifiedCollection[VoiceUnion] = IdentifiedCollection()
        voices.append(Instrument(name="Lead", envelopes=InstrumentEnvelopes(volume=Envelope(items=(15, 0)))))
        project = Project.create(title="Instruments", author="Tester", settings=ProjectSettings())
        project.voices = voices

        song = project_to_bitphase(project).songs[0]

        assert song.a4_tuning_hz == DEFAULT_A4_TUNING
        assert song.tuning_table == DEFAULT_TUNING_TABLE


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


def played_volumes(document: BitphaseProject, channel: ChannelIndex) -> List[int]:
    """The level Bitphase plays one channel at on each row, the order played through and round again.

    The document returns to its loop point, the first order position, keeping every channel's level,
    so a second pass shows what the level the song ends on does to the notes it opens with.
    """
    patterns = {pattern.id: pattern for pattern in document.songs[0].patterns}
    level = BITPHASE_OPENING_PATTERN_VOLUME
    levels: List[int] = []
    for _ in range(PLAYED_PASSES):
        for pattern_id in document.pattern_order:
            for row in patterns[pattern_id].channels[int(channel)].rows:
                level = pattern_volume(level, row.volume)
                levels.append(level)

    return levels


def cell_pitch(note: NoteCell) -> int:
    """The pitch a pattern cell's note column names."""
    return (note.name - int(NoteName.C)) + (note.octave - FIRST_OCTAVE) * NOTE_RANGE + NOTE_INDEX_PITCH_OFFSET


class TestTheLevelsAPlayedSongCarries:
    """The song starts a note stating no level at the full level and sounds the triangle only above
    half volume, while Bitphase carries the last level a cell wrote into every note and sounds the
    triangle at any level above silence. The document therefore writes its volume column so that
    Bitphase, playing the order through and round again, plays each row the song sounds at the song's
    own level.
    """

    @pytest.fixture(name="arranged")
    def arranged_fixture(self, lead: Sample, bass: Sample) -> Project:
        lead_note = Row(command=NoteOn(voice_id=lead.id))
        bass_note = Row(command=NoteOn(voice_id=bass.id))
        pulse = {
            0: rows_with(
                (0, lead_note),
                (1, Row(volume=QUIET_VOLUME)),
                (2, Row(transpose=TRANSPOSE)),
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
        played = played_volumes(project_to_bitphase(arranged), ChannelIndex.SQUARE1)
        song = song_row_volumes(arranged.song, ChannelName.PULSE1) * PLAYED_PASSES

        sounding = [(level, volume) for level, volume in zip(played, song) if volume is not None]
        assert [level for level, _ in sounding] == [volume for _, volume in sounding]

    def test_the_triangle_sounds_on_every_row_the_song_sounds_it(self, arranged: Project) -> None:
        played = played_volumes(project_to_bitphase(arranged), ChannelIndex.TRIANGLE)
        song = song_row_volumes(arranged.song, ChannelName.TRIANGLE) * PLAYED_PASSES

        sounding = [(level, volume) for level, volume in zip(played, song) if volume is not None]
        assert [level > 0 for level, _ in sounding] == [triangle_sounds_at(volume) for _, volume in sounding]

    def test_a_note_the_song_ends_quieter_than_writes_the_full_level(self, arranged: Project) -> None:
        """The order returns to its first frame carrying the level its last frame set, so the song's
        opening note is written at the full level although the first pass reaches it there anyway.
        """
        row = project_to_bitphase(arranged).songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[0]
        assert row.volume == FULL_VOLUME


class TestTheTriangleSoundsAboveHalfVolume(BaseTestSuite):
    """The song sounds the triangle while a row asks for more than half volume, while Bitphase sounds
    it at any pattern level above silence, so a quieter row writes the value that silences it.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        volume: int
        expected: int

    test_cases: Tuple["TestTheTriangleSoundsAboveHalfVolume.TestCase", ...] = (
        TestCase(label="a level the triangle rests at", volume=QUIET_TRIANGLE_VOLUME, expected=VOLUME_OFF),
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

        row = project_to_bitphase(project).songs[0].patterns[0].channels[int(ChannelIndex.TRIANGLE)].rows[0]

        assert row.volume == test_case.expected


class TestALowTransposeKeepsTheSongsPitch:
    """The song holds every tick's transposed pitch within 33-119, while Bitphase at concert pitch plays
    any note below 33 at its longest period, a little flat of the lowest pitch. A transpose below the
    range therefore raises the note only as far as the contour's highest step reaching the lowest pitch.
    """

    @staticmethod
    def _transposed(sample: Sample, transpose: int) -> Tuple[BitphaseProject, BitphaseRow]:
        project = arranged_project(
            (sample,),
            {ChannelName.PULSE1: {0: rows_with((0, Row(command=NoteOn(voice_id=sample.id), transpose=transpose)))}},
            [{ChannelName.PULSE1: 0}],
        )
        document = project_to_bitphase(project)
        return (
            document,
            document.songs[0].patterns[0].channels[int(ChannelIndex.SQUARE1)].rows[0],
        )

    def test_a_flat_voice_transposed_below_the_range_writes_the_lowest_note(self) -> None:
        _, row = self._transposed(pulse_sample("Low", LOW_PITCH, config=Config()), LOW_TRANSPOSE)

        assert cell_pitch(row.note) == MIN_PITCH

    def test_a_contour_reaching_into_the_range_keeps_every_tick_the_song_plays_there(self) -> None:
        sample = contour_sample("Contour", CONTOUR_PITCHES, config=Config())
        document, row = self._transposed(sample, STRADDLING_TRANSPOSE)

        reference = voice_reference(sample, ChannelName.PULSE1)
        steps = document.tables[0].rows
        written = cell_pitch(row.note) - NOTE_INDEX_PITCH_OFFSET
        tracker = [min(max(written + step, MIN_NOTE_INDEX), MAX_NOTE_INDEX) + NOTE_INDEX_PITCH_OFFSET for step in steps]
        song = [transpose_pitch(reference + step, STRADDLING_TRANSPOSE) for step in steps]

        assert cell_pitch(row.note) == reference + STRADDLING_TRANSPOSE
        assert [pitch for pitch, sung in zip(tracker, song) if sung > MIN_PITCH] == [
            sung for sung in song if sung > MIN_PITCH
        ]

    def test_a_contour_lying_below_the_range_sounds_its_highest_step_at_the_lowest_pitch(self) -> None:
        sample = contour_sample("Contour", CONTOUR_PITCHES, config=Config())
        document, row = self._transposed(sample, SUBMERGED_TRANSPOSE)

        assert cell_pitch(row.note) + max(document.tables[0].rows) == MIN_PITCH
