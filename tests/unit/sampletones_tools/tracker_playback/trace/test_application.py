from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import Groove
from sampletones_player.registers.base import ChannelRegisters
from sampletones_tools.tracker_playback.trace.application import (
    application_trace,
    register_sound,
    song_positions,
)
from sampletones_tools.tracker_playback.trace.sound import ABSENT_REGISTER, ChannelSound, TickPosition
from tests.suite.performance import (
    make_pulse_reconstruction,
    place_instrument,
    project_with_sample,
)
from tests.suite.player import (
    PLAYER_TIMER_TABLE,
    noise_tick,
    pulse_tick,
    triangle_tick,
)

TICKS_PER_ROW: Final[int] = 6
ROWS_PER_PATTERN: Final[int] = 2
SETTINGS: Final[ProjectSettings] = ProjectSettings(tempo=150, speed=TICKS_PER_ROW, nes_frequency=60)
PITCH: Final[int] = 60
FRAMES: Final[int] = 8
ROW_VOLUME: Final[int] = 5


class TestSongPositions:
    def test_each_row_lasts_the_ticks_its_groove_gives_it_in_every_frame(self) -> None:
        positions = song_positions(Groove(ticks=(2, 1)), 2)

        assert positions == (
            TickPosition(frame=0, row=0),
            TickPosition(frame=0, row=0),
            TickPosition(frame=0, row=1),
            TickPosition(frame=1, row=0),
            TickPosition(frame=1, row=0),
            TickPosition(frame=1, row=1),
        )


class TestRegisterSound:
    def test_a_pulse_reads_its_level_duty_and_timer(self) -> None:
        assert register_sound(pulse_tick(9, 3, 427)) == ChannelSound(audible=True, period=427, volume=9, timbre=3)

    def test_a_pulse_at_level_zero_is_silent(self) -> None:
        assert not register_sound(pulse_tick(0, 3, 427)).audible

    def test_a_triangle_sounds_while_its_linear_counter_reloads(self) -> None:
        sounding = register_sound(triangle_tick(True, 854))

        assert sounding == ChannelSound(audible=True, period=854, volume=ABSENT_REGISTER, timbre=ABSENT_REGISTER)
        assert not register_sound(triangle_tick(False, 854)).audible

    def test_the_noise_reads_its_level_its_register_period_and_its_mode(self) -> None:
        assert register_sound(noise_tick(12, 1, 9)) == ChannelSound(audible=True, period=9, volume=12, timbre=1)


class UnplayedRegisters(ChannelRegisters):
    @property
    def values(self) -> Tuple[int, ...]:
        return ()


class TestUnplayedRegisters:
    def test_registers_of_no_channel_the_console_plays_are_refused(self) -> None:
        with pytest.raises(TypeError, match="UnplayedRegisters"):
            register_sound(UnplayedRegisters())


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
