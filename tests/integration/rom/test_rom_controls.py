from dataclasses import dataclass
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_core.project.voices.sample import Sample
from sampletones_player.song import Song
from sampletones_player.specification.registers import (
    NOISE_CONTROL,
    PULSE1_CONTROL,
    PULSE2_CONTROL,
    SUSTAINED_LEVEL,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_LINEAR_COUNTER,
    TRIANGLE_SILENT_RELOAD,
)
from sampletones_tools.console.rom.controller import Button
from sampletones_tools.console.rom.machine import ROMConsole
from sampletones_tools.player.trace.trace import RegisterTrace
from sampletones_tools.player.trace.write import RegisterWrite
from tests.integration.nsf.console.session import play_calls_covering
from tests.integration.nsf.header import sample_information
from tests.integration.rom.session import booted, cartridge, reclocked_song, run_frames
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.player import PLAYER_SILENT_VOLUME

NTSC_RATE: Final[int] = 60
HALF_RATE: Final[int] = 30
PAUSE_AT: Final[int] = 9
PAUSED_FRAMES: Final[int] = 5
RESUMED_FRAMES: Final[int] = 12
RESTART_AT: Final[int] = 13
RESTARTED_FRAMES: Final[int] = 20
SILENT_LEVEL: Final[int] = SUSTAINED_LEVEL | PLAYER_SILENT_VOLUME
SILENT_LINEAR_COUNTER: Final[int] = TRIANGLE_COUNTER_CONTROL | TRIANGLE_SILENT_RELOAD
MUTED: Final[Tuple[RegisterWrite, ...]] = (
    RegisterWrite(PULSE1_CONTROL, SILENT_LEVEL),
    RegisterWrite(PULSE2_CONTROL, SILENT_LEVEL),
    RegisterWrite(NOISE_CONTROL, SILENT_LEVEL),
    RegisterWrite(TRIANGLE_LINEAR_COUNTER, SILENT_LINEAR_COUNTER),
)

Sound = Tuple[RegisterWrite, ...]


def console_of(song: Song, sample: Sample) -> ROMConsole:
    return booted(cartridge(song, sample_information(sample.name)))


def expected_trace(song: Song) -> RegisterTrace:
    """The writes the model states over a run reaching past the song's end and the controls' frames."""
    return RegisterTrace.from_song(song, play_calls_covering(song) + RESTARTED_FRAMES)


class TestAPause:
    """START silences every channel and holds the song where it stands."""

    @pytest.fixture
    def sounds(self, song: Song, sample: Sample) -> List[Sound]:
        """The writes of every frame up to the one START is read in, of that frame and of the paused ones after it."""
        console = console_of(song, sample)
        frames = run_frames(console, PAUSE_AT - 1)
        frames.append(console.frame(Button.START))
        frames.extend(run_frames(console, PAUSED_FRAMES))
        return [frame.sound for frame in frames]

    def test_the_frame_start_is_read_in_still_plays(self, sounds: List[Sound], song: Song) -> None:
        played = expected_trace(song).play_calls

        assert sounds[: PAUSE_AT - 1] == list(played[: PAUSE_AT - 1])
        assert sounds[PAUSE_AT - 1][: len(played[PAUSE_AT - 1])] == played[PAUSE_AT - 1]

    def test_the_pause_writes_the_four_mutes_alone(self, sounds: List[Sound], song: Song) -> None:
        played = expected_trace(song).play_calls[PAUSE_AT - 1]

        assert sorted(sounds[PAUSE_AT - 1][len(played) :]) == sorted(MUTED)

    def test_nothing_plays_while_paused(self, sounds: List[Sound]) -> None:
        assert sounds[PAUSE_AT:] == [()] * PAUSED_FRAMES


class TestResumingPlaysOnFromThePause(BaseTestSuite):
    """The song resumes on the very play call the pause held it before, at any rate it was built at."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        nes_frequency: int

    test_cases = (
        TestCase(label="60-hz", nes_frequency=NTSC_RATE),
        TestCase(label="30-hz", nes_frequency=HALF_RATE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_writes_after_resuming_are_the_model_s_from_the_pause_on(
        self, test_case: TestCase, sample: Sample
    ) -> None:
        song = reclocked_song(sample, test_case.nes_frequency, looping=False)
        console = console_of(song, sample)
        run_frames(console, PAUSE_AT - 1)
        console.frame(Button.START)
        run_frames(console, PAUSED_FRAMES)

        resumed = console.frame(Button.START)
        after = [frame.sound for frame in run_frames(console, RESUMED_FRAMES)]

        played = expected_trace(song).play_calls
        assert resumed.sound == ()
        assert after == list(played[PAUSE_AT : PAUSE_AT + RESUMED_FRAMES])


class TestSelectStartsTheSongOver(BaseTestSuite):
    """SELECT clears the driver and starts the song again, from wherever it stood and however it stood."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        played: Callable[[Song], int]
        paused: bool

    test_cases = (
        TestCase(label="while-playing", played=lambda song: RESTART_AT, paused=False),
        TestCase(label="while-paused", played=lambda song: RESTART_AT, paused=True),
        TestCase(label="after-the-end", played=play_calls_covering, paused=False),
    )

    @staticmethod
    def restarted(console: ROMConsole, test_case: TestCase, song: Song) -> List[Sound]:
        """The writes of the frame SELECT is read in and of every frame after it."""
        run_frames(console, test_case.played(song))
        if test_case.paused:
            console.frame(Button.START)

        frames = [console.frame(Button.SELECT), *run_frames(console, RESTARTED_FRAMES)]
        return [frame.sound for frame in frames]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_song_is_initialized_again_in_the_frame_select_is_read_in(
        self, test_case: TestCase, song: Song, sample: Sample
    ) -> None:
        sounds = self.restarted(console_of(song, sample), test_case, song)
        initialization = expected_trace(song).initialization

        assert sounds[0][-len(initialization) :] == initialization

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_frames_after_it_play_the_song_from_its_start(
        self, test_case: TestCase, song: Song, sample: Sample
    ) -> None:
        sounds = self.restarted(console_of(song, sample), test_case, song)

        assert sounds[1:] == list(expected_trace(song).play_calls[:RESTARTED_FRAMES])
