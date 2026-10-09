from dataclasses import dataclass
from typing import Final, List, Optional

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import (
    InstructionUnion,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones_core.performance import WalkProgress, song_instructions
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from sampletones_shared.exceptions import OperationCanceled
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.performance import (
    make_pulse_reconstruction,
    place_instrument,
    project_with_instrument,
    project_with_sample,
)

ROWS_PER_PATTERN: Final[int] = 4
ENVELOPE_TICKS: Final[int] = 2
SETTINGS: Final[ProjectSettings] = ProjectSettings(tempo=150, speed=6, nes_frequency=60)
FOLLOWER_PITCH: Final[int] = 57
FOLLOWER_PERIOD: Final[int] = 4
ROW_VOLUME: Final[int] = 10
LEADER_ENVELOPES: Final[InstrumentEnvelopes] = InstrumentEnvelopes(
    volume=Envelope(items=(6,)),
    arpeggio=Envelope(items=(7,)),
    pitch=Envelope(items=(-3,)),
    hi_pitch=Envelope(items=(1,)),
    duty_cycle=Envelope(items=(1,)),
)
RELEASED_ENVELOPES: Final[InstrumentEnvelopes] = InstrumentEnvelopes(
    volume=Envelope(items=(MAX_VOLUME, 0)),
    duty_cycle=Envelope(items=(1,)),
)


def _project() -> Project:
    """A one-frame project sounding a two-tick pulse envelope from the first row."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(count=ENVELOPE_TICKS),
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=SETTINGS,
    )
    place_instrument(
        project,
        channel_name=ChannelName.PULSE1,
        row_index=0,
        sample=sample,
    )
    return project


def _resting(channel_name: ChannelName) -> object:
    return CHANNEL_TO_EXPORTER_MAP[channel_name].get_instruction_type().null_instruction()


class TestSongInstructions:
    """The four streams a song plays out as, one instruction per channel per engine tick."""

    def test_the_song_lasts_the_ticks_its_timing_gives_every_row_it_plays(self) -> None:
        project = _project()
        timing = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS)

        streams = song_instructions(project)

        assert len(streams[ChannelName.PULSE1]) == timing.frame_tick(project.song.order_length())

    def test_a_row_starts_on_the_tick_the_timing_places_it_at(self) -> None:
        """At tempo 125 a row lasts 7.2 ticks, so a pattern played again starts where its frame's bar line falls."""
        project = _project()
        project.settings = SETTINGS.model_copy(update={"tempo": 125})
        project.song.append_frame()
        project.song.set_order_entry(1, ChannelName.PULSE1, 0)
        start = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).tick_at(1, 0)

        stream = song_instructions(project)[ChannelName.PULSE1]

        assert stream[start - 1] == _resting(ChannelName.PULSE1)
        assert stream[start] == stream[0]

    def test_every_channel_answers_for_every_tick(self) -> None:
        """One length across the four streams is what makes a tick index one moment of the song."""
        streams = song_instructions(_project())

        assert len({len(stream) for stream in streams.values()}) == 1

    def test_a_channel_no_row_names_rests_throughout(self) -> None:
        streams = song_instructions(_project())

        assert streams[ChannelName.TRIANGLE] == [_resting(ChannelName.TRIANGLE)] * len(streams[ChannelName.TRIANGLE])

    def test_a_sounding_channel_falls_silent_once_its_envelope_plays_out(self) -> None:
        """A one-shot sounds for the ticks it carries and rests for the rest of the row."""
        stream = song_instructions(_project())[ChannelName.PULSE1]
        resting = _resting(ChannelName.PULSE1)

        assert stream[:ENVELOPE_TICKS] != [resting] * ENVELOPE_TICKS
        assert stream[ENVELOPE_TICKS:] == [resting] * (len(stream) - ENVELOPE_TICKS)

    def test_a_pattern_the_order_plays_twice_sounds_alike_both_times(self) -> None:
        """The order is where reuse lives, so the ticks a repeated frame produces are the same."""
        project = _project()
        project.song.append_frame()
        project.song.set_order_entry(1, ChannelName.PULSE1, 0)
        timing = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS)

        stream = song_instructions(project)[ChannelName.PULSE1]

        frame_ticks = timing.frame_tick(1)
        assert stream[:frame_ticks] == stream[frame_ticks : timing.frame_tick(2)]


class TestWhatAWalkSaysAboutItself:
    """A song of minutes is played out row by row, so the walk says how far along it is."""

    def test_the_walk_reports_each_row_it_sounds(self) -> None:
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        assert len(heard) == project.song.order_length() * project.song.rows_per_pattern

    def test_the_walk_states_the_ticks_the_order_lasts(self) -> None:
        """The timing states the length before a row is played, so every report names the same."""
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        expected = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).frame_tick(project.song.order_length())
        assert [progress.total for progress in heard] == [expected] * len(heard)

    def test_the_walk_reaches_the_ticks_it_set_out_to_sound(self) -> None:
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        assert heard[-1].ticks == heard[-1].total

    def test_the_walk_counts_up_as_it_goes(self) -> None:
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        counted = [progress.ticks for progress in heard]
        assert counted == sorted(counted)

    def test_a_withdrawn_walk_stops_where_it_was_told(self) -> None:
        with pytest.raises(OperationCanceled):
            song_instructions(_project(), lambda progress: False)


def _following(
    leader: InstrumentEnvelopes,
    follower: InstrumentEnvelopes,
    channel_name: ChannelName,
    *,
    volume: Optional[int] = None,
) -> InstructionUnion:
    """The first frame a voice sounds on the row after a whole row of another voice."""
    first = Instrument(name="leader", envelopes=leader)
    second = Instrument(
        name="follower",
        envelopes=follower,
        initial_pitch=FOLLOWER_PITCH,
        initial_period=FOLLOWER_PERIOD,
    )
    project = project_with_instrument(first, rows_per_pattern=ROWS_PER_PATTERN, settings=SETTINGS)
    project.voices.append(second)
    place_instrument(project, channel_name=channel_name, row_index=0, sample=first, transpose=0)
    place_instrument(project, channel_name=channel_name, row_index=1, sample=second, transpose=0, volume=volume)

    stream = song_instructions(project)[channel_name]
    return stream[SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).row_ticks(0, 0)]


class TestANoteStartsFromWhereASongStarts(BaseTestSuite):
    """A voice leaving a dimension empty sounds it where a song starts it, whatever came before.

    The note before writes every dimension away from that start. The note after writes one
    dimension, leaves the rest empty, and sounds full volume, no arpeggio offset, no bend, and the
    first duty cycle or the long noise mode, which is how FamiTracker and Bitphase start a note.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel_name: ChannelName
        follower: InstrumentEnvelopes
        expected: InstructionUnion

    test_cases = (
        TestCase(
            label="pulse leaving its arpeggio, bend and duty cycle",
            channel_name=ChannelName.PULSE1,
            follower=InstrumentEnvelopes(volume=Envelope(items=(MAX_VOLUME,))),
            expected=PulseInstruction(
                on=True,
                pitch=FOLLOWER_PITCH,
                volume=MAX_VOLUME,
                duty_cycle=0,
                detune=0,
                coarse_detune=0,
            ),
        ),
        TestCase(
            label="pulse leaving its volume",
            channel_name=ChannelName.PULSE1,
            follower=InstrumentEnvelopes(arpeggio=Envelope(items=(0,))),
            expected=PulseInstruction(
                on=True,
                pitch=FOLLOWER_PITCH,
                volume=MAX_VOLUME,
                duty_cycle=0,
                detune=0,
                coarse_detune=0,
            ),
        ),
        TestCase(
            label="triangle leaving its arpeggio and bend",
            channel_name=ChannelName.TRIANGLE,
            follower=InstrumentEnvelopes(volume=Envelope(items=(MAX_VOLUME,))),
            expected=TriangleInstruction(
                on=True,
                pitch=FOLLOWER_PITCH,
                detune=0,
                coarse_detune=0,
            ),
        ),
        TestCase(
            label="noise leaving its arpeggio and mode",
            channel_name=ChannelName.NOISE,
            follower=InstrumentEnvelopes(volume=Envelope(items=(MAX_VOLUME,))),
            expected=NoiseInstruction(
                on=True,
                period=FOLLOWER_PERIOD,
                volume=MAX_VOLUME,
                short=False,
            ),
        ),
        TestCase(
            label="noise leaving its volume",
            channel_name=ChannelName.NOISE,
            follower=InstrumentEnvelopes(arpeggio=Envelope(items=(0,))),
            expected=NoiseInstruction(
                on=True,
                period=FOLLOWER_PERIOD,
                volume=MAX_VOLUME,
                short=False,
            ),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_note_after_sounds_the_empty_dimensions_at_their_start(self, test_case: TestCase) -> None:
        sounded = _following(LEADER_ENVELOPES, test_case.follower, test_case.channel_name)

        assert sounded == test_case.expected

    @pytest.mark.parametrize(
        "channel_name",
        (ChannelName.PULSE1, ChannelName.NOISE),
        ids=lambda channel_name: channel_name.value,
    )
    def test_a_voice_leaving_its_volume_sounds_at_the_rows_after_one_that_released(
        self,
        channel_name: ChannelName,
    ) -> None:
        """A note that ended at silence leaves the next one its row's level, the way a tracker plays it."""
        sounded = _following(
            RELEASED_ENVELOPES,
            InstrumentEnvelopes(arpeggio=Envelope(items=(0, 12), loop_point=0)),
            channel_name,
            volume=ROW_VOLUME,
        )

        assert isinstance(sounded, (PulseInstruction, NoiseInstruction))
        assert sounded.on is True
        assert sounded.volume == ROW_VOLUME


class TestAnInstrumentGoesOnFromTheSamplesPitch:
    """An instrument placed without a pitch sounds on the pitch the sample before it reached, envelopes restarted."""

    def test_the_instruments_first_tick_sounds_at_the_samples_pitch(self) -> None:
        project, sample = project_with_sample(
            make_pulse_reconstruction(pitch=FOLLOWER_PITCH, count=ENVELOPE_TICKS),
            rows_per_pattern=ROWS_PER_PATTERN,
            settings=SETTINGS,
        )
        lead = Instrument(name="lead", envelopes=LEADER_ENVELOPES, initial_pitch=FOLLOWER_PITCH + 12)
        project.voices.append(lead)
        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=sample, transpose=5)
        project.song.channels[ChannelName.PULSE1].ensure_pattern(0, ROWS_PER_PATTERN)
        project.song.channels[ChannelName.PULSE1].set_row(0, 2, Row(command=NoteOn(voice_id=lead.id)))
        timing = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS)

        stream = song_instructions(project)[ChannelName.PULSE1]

        first = stream[timing.frame_tick(0) + sum(timing.row_ticks(0, row) for row in range(2))]
        assert isinstance(first, PulseInstruction)
        assert first.pitch == FOLLOWER_PITCH + 5 + LEADER_ENVELOPES.arpeggio.items[0]

    def test_an_instrument_placed_on_a_silent_channel_sounds_nothing(self) -> None:
        project = project_with_instrument(
            Instrument(name="lead", envelopes=LEADER_ENVELOPES),
            rows_per_pattern=ROWS_PER_PATTERN,
            settings=SETTINGS,
        )
        lead = project.voices[0]
        channel = project.song.channels[ChannelName.PULSE1]
        channel.ensure_pattern(0, ROWS_PER_PATTERN)
        channel.set_row(0, 0, Row(command=NoteOn(voice_id=lead.id)))
        channel.set_row(0, 2, Row(command=NoteOn(voice_id=lead.id), pitch=Step(value=0)))
        timing = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS)

        stream = song_instructions(project)[ChannelName.PULSE1]

        sounding_from = sum(timing.row_ticks(0, row) for row in range(2))
        assert all(instruction == _resting(ChannelName.PULSE1) for instruction in stream[:sounding_from])
        assert stream[sounding_from] != _resting(ChannelName.PULSE1)
