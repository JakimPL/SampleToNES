from fractions import Fraction
from typing import Final

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SONG_TICK_BOUNDS, Meter, RowRate, SongTiming
from sampletones_player.specification.registers import (
    APU_STATUS,
    CHANNELS_ENABLED,
    PULSE1_CONTROL,
    PULSE1_SWEEP,
    PULSE2_SWEEP,
    SWEEP_DISABLED,
)
from sampletones_tools.tracker_playback.trace.application import (
    application_trace,
    driver_registers,
    song_positions,
)
from sampletones_tools.tracker_playback.trace.sound import ChannelSound, TickPosition
from tests.suite.performance import (
    make_pulse_reconstruction,
    place_instrument,
    project_with_sample,
)
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    PLAYER_TIMER_TABLE,
    pulse_tick,
    resting_streams,
)

TICKS_PER_ROW: Final[int] = 6
ROWS_PER_PATTERN: Final[int] = 2
SETTINGS: Final[ProjectSettings] = ProjectSettings(tempo=150, speed=TICKS_PER_ROW, nes_frequency=60)
PITCH: Final[int] = 60
FRAMES: Final[int] = 8
ROW_VOLUME: Final[int] = 5


class TestSongPositions:
    def test_each_row_lasts_the_ticks_its_frame_gives_it(self) -> None:
        """At 5/4 ticks a row a 2-row pattern lasts 2.5 ticks, so the first frame plays 3 and the second 2."""
        timing = SongTiming(
            rate=RowRate(ticks_per_row=Fraction(5, 4)),
            meter=Meter(rows=2, first_highlight=2, second_highlight=2),
            bounds=SONG_TICK_BOUNDS,
        )

        positions = song_positions(timing, 2)

        assert positions == (
            TickPosition(frame=0, row=0),
            TickPosition(frame=0, row=0),
            TickPosition(frame=0, row=1),
            TickPosition(frame=1, row=0),
            TickPosition(frame=1, row=1),
        )


class TestDriverRegisters:
    SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
    OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)
    RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)

    def test_the_console_stands_where_the_drivers_init_routine_leaves_it(self) -> None:
        (registers,) = driver_registers(resting_streams((self.SOUNDING,)), 1)

        assert registers.value(APU_STATUS) == CHANNELS_ENABLED
        assert (registers.value(PULSE1_SWEEP), registers.value(PULSE2_SWEEP)) == (SWEEP_DISABLED, SWEEP_DISABLED)

    def test_each_tick_holds_the_values_its_channels_write(self) -> None:
        registers = driver_registers(resting_streams((self.SOUNDING, self.OCTAVE_UP)), 2)

        assert [tick.value(PULSE1_CONTROL) for tick in registers] == [self.SOUNDING.control, self.OCTAVE_UP.control]

    def test_a_channel_past_the_end_of_its_stream_holds_its_final_values(self) -> None:
        registers = driver_registers(resting_streams((self.SOUNDING, self.RESTING)), 4)

        assert registers[-1] == registers[1]


class TestApplicationTrace:
    def test_a_sample_sounds_its_frames_at_the_row_volume_and_then_rests(self) -> None:
        project, sample = project_with_sample(
            make_pulse_reconstruction(pitch=PITCH, count=FRAMES),
            rows_per_pattern=ROWS_PER_PATTERN,
            settings=SETTINGS,
        )
        place_instrument(
            project,
            channel_name=ChannelName.PULSE1,
            row_index=0,
            sample=sample,
            volume=ROW_VOLUME,
        )

        trace = application_trace(project)

        pulse = trace.channels[ChannelName.PULSE1]
        assert trace.ticks == ROWS_PER_PATTERN * TICKS_PER_ROW
        assert trace.positions[TICKS_PER_ROW] == TickPosition(frame=0, row=1)
        assert pulse[0] == ChannelSound(
            audible=True,
            period=PLAYER_TIMER_TABLE[PITCH],
            volume=ROW_VOLUME,
            held=True,
            timbre=0,
        )
        assert all(sound.audible for sound in pulse[:FRAMES])
        assert not any(sound.audible for sound in pulse[FRAMES:])
        assert not any(sound.audible for sound in trace.channels[ChannelName.NOISE])

    def test_every_channel_covers_every_tick_of_the_order(self) -> None:
        project, _ = project_with_sample(
            make_pulse_reconstruction(count=FRAMES),
            rows_per_pattern=ROWS_PER_PATTERN,
            settings=SETTINGS,
        )
        project.song.append_frame()

        trace = application_trace(project)

        assert trace.ticks == 2 * ROWS_PER_PATTERN * TICKS_PER_ROW
        assert {len(sounds) for sounds in trace.channels.values()} == {trace.ticks}
