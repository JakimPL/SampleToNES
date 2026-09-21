from dataclasses import dataclass
from typing import Final, List, Self, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH, PITCH_BEND_MAX, PITCH_BEND_MIN
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.timers.arithmetic import bent_timer
from sampletones_player.builder import song_from_reconstruction, streams_from_instructions
from sampletones_player.compression.decode import decode_planes
from sampletones_player.specification.planes import PlaneRole, plane_index
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.song import Song
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.registers import PULSE1_TIMER_HIGH, TIMER_HIGH_SHIFT
from sampletones_tools.player.trace.trace import RegisterTrace
from tests.integration.nsf.console.instructions import channel_values, timer_value
from tests.integration.nsf.console.machine import register_file
from tests.integration.nsf.console.session import (
    captured_trace,
    captured_trace_over,
    play_calls_covering,
    play_calls_reaching,
)
from tests.integration.nsf.header import sample_information
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_PITCHES,
    PLAYER_REFERENCE_PITCH,
    PLAYER_TIMER_TABLE,
    bent_song,
    player_reconstruction,
    player_song,
)

NTSC_RATE: Final[int] = 60
SONG_NAME: Final[str] = "bend"

MIDRANGE_INDEX: Final[int] = 33
BOUNDARY_INDEX: Final[int] = 17
WIDEST_RESIDUAL: Final[int] = 57
TIMER_LOW_INDEX: Final[int] = 1
TIMER_HIGH_INDEX: Final[int] = 2
VIBRATO: Final[Tuple[int, ...]] = (0, 3, 6, 3, 0, -3, -6, -3, 0)
SLIDE: Final[Tuple[int, ...]] = tuple(range(0, -70, -10))
COARSE_STEPS: Final[int] = 10


def sounded_dividers(song: Song) -> List[int]:
    """The divider the console leaves on the first pulse channel after each tick it sounds.

    Args:
        song: The song to export and run.

    Returns:
        List[int]: One divider per tick the song covers, in order.
    """
    trace = captured_trace(song, sample_information(SONG_NAME))
    dividers = []
    for registers in register_file(trace):
        values = channel_values(registers, ChannelName.PULSE1)
        dividers.append(timer_value(values[TIMER_LOW_INDEX], values[TIMER_HIGH_INDEX]))

    return dividers[: song.planes.ticks]


class TestTheDriverSoundsTheDividerABendPlaneNames(BaseTestSuite):
    """The assembled 6502 driver run on py65, its timer registers read back tick by tick.

    A plane byte reaches the timer through a sign extension and a sixteen-bit add, which is the
    one piece of arithmetic the driver performs on a song's behalf. These runs state a bend plane
    outright, bends past the room a nearest pitch leaves included, and hold the console to the
    divider each tick is meant to sound at.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        """One run of a bent note, and the divider each of its ticks reaches.

        Attributes:
            pitch_index: The pitch the value plane names throughout.
            bends: The divider steps each tick stands away from that pitch.
            expected: The divider each tick sounds at.
        """

        pitch_index: int
        bends: Tuple[int, ...]
        expected: Tuple[int, ...]

        @classmethod
        def bending(cls, pitch_index: int, bends: Tuple[int, ...]) -> Self:
            """A case whose expectation is the note's own divider moved by each bend."""
            return cls(
                pitch_index=pitch_index,
                bends=bends,
                expected=tuple(PLAYER_PITCHES.timers[pitch_index] + bend for bend in bends),
            )

        @property
        def label(self) -> str:
            return f"pitch {self.pitch_index} bent {' '.join(f'{bend:+d}' for bend in self.bends)}"

    test_cases = (
        TestCase.bending(MIDRANGE_INDEX, (0, 0, 0, 0)),
        TestCase.bending(MIDRANGE_INDEX, (0, 7, 3, 0)),
        TestCase.bending(MIDRANGE_INDEX, (0, -7, -3, 0)),
        TestCase.bending(MIDRANGE_INDEX, (WIDEST_RESIDUAL, -WIDEST_RESIDUAL, 0, 1)),
        TestCase.bending(BOUNDARY_INDEX, (0, -1, 3, -2)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_console_sounds_the_divider_the_bend_states(self, test_case: TestCase) -> None:
        song = bent_song(test_case.pitch_index, test_case.bends, NTSC_RATE)
        assert sounded_dividers(song) == list(test_case.expected)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_model_states_the_writes_the_driver_makes(self, test_case: TestCase) -> None:
        song = bent_song(test_case.pitch_index, test_case.bends, NTSC_RATE)
        trace = captured_trace(song, sample_information(SONG_NAME))
        assert trace == RegisterTrace.from_song(song, play_calls_covering(song))


class TestABendCrossingTheTimersHighHalf:
    """A divider whose high half moves is where the driver's carry and its shadow both show.

    The high half reaches the register only where it differs from the last one written, so a bend
    that carries into it is the one that proves the carry survives the two halves of the add and
    that the shadow follows what was actually written.
    """

    BENDS: Final[Tuple[int, ...]] = (0, -1, 3, -2)

    @pytest.fixture
    def crossing(self) -> Song:
        """A note standing on a high-byte boundary, bent to either side of it."""
        return bent_song(BOUNDARY_INDEX, self.BENDS, NTSC_RATE)

    def test_the_note_stands_on_a_boundary(self) -> None:
        assert PLAYER_PITCHES.timers[BOUNDARY_INDEX] % BYTE_VALUES == 0

    def test_the_carry_reaches_the_timers_high_half(self, crossing: Song) -> None:
        divider = PLAYER_PITCHES.timers[BOUNDARY_INDEX]
        assert sounded_dividers(crossing) == [divider + bend for bend in self.BENDS]

    def test_the_high_half_is_written_wherever_the_bend_moves_it(self, crossing: Song) -> None:
        divider = PLAYER_PITCHES.timers[BOUNDARY_INDEX]
        halves = [(divider + bend) >> TIMER_HIGH_SHIFT for bend in self.BENDS]
        crossings = sum(1 for earlier, later in zip(halves, halves[1:]) if earlier != later)

        trace = captured_trace(crossing, sample_information(SONG_NAME))
        written = [write for writes in trace.play_calls for write in writes if write.address == PULSE1_TIMER_HIGH]
        assert crossings
        assert len(written) == crossings


class TestTheConsoleSoundsTheBendAFrameCarries(BaseTestSuite):
    """Bent frames exported the way a reconstruction is, played on py65 and read back per tick.

    This is the whole path a bend takes: the encoders write the divider the generators render,
    the planes split it into a note and a bend, the codec compresses both, and the driver adds
    them back. Every tick is held to the divider the sequencer sounds the frame at.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        """A run of bent frames on the first pulse channel.

        Attributes:
            name: What the run shows.
            frames: The frames the channel plays.
        """

        expected: None = None
        name: str
        frames: Tuple[PulseInstruction, ...]

        @classmethod
        def bent(cls, name: str, pitch: int, bends: Tuple[Tuple[int, int], ...]) -> Self:
            """A case holding one note while each frame bends it by a fine and a coarse step count."""
            return cls(
                name=name,
                frames=tuple(
                    PulseInstruction(
                        on=True,
                        pitch=pitch,
                        volume=PLAYER_FULL_VOLUME,
                        duty_cycle=0,
                        detune=detune,
                        coarse_detune=coarse_detune,
                    )
                    for detune, coarse_detune in bends
                ),
            )

        @property
        def label(self) -> str:
            return self.name

    test_cases = (
        TestCase.bent("vibrato", PLAYER_REFERENCE_PITCH, tuple((bend, 0) for bend in VIBRATO)),
        TestCase.bent("slide into the next note", PLAYER_REFERENCE_PITCH, tuple((bend, 0) for bend in SLIDE)),
        TestCase.bent(
            "coarse bend past a byte", PLAYER_REFERENCE_PITCH, ((0, 0), (0, COARSE_STEPS), (1, COARSE_STEPS))
        ),
        TestCase.bent("clamped at the slowest divider", MIN_PITCH, ((0, 0), (PITCH_BEND_MAX, PITCH_BEND_MAX))),
        TestCase.bent("clamped at the fastest divider", MAX_PITCH, ((0, 0), (PITCH_BEND_MIN, PITCH_BEND_MIN))),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_every_tick_sounds_the_divider_the_sequencer_renders(self, test_case: TestCase) -> None:
        instructions: List[InstructionUnion] = list(test_case.frames)
        song = song_from_reconstruction(
            player_reconstruction({ChannelName.PULSE1: instructions}, NTSC_RATE),
            loop_tick=None,
            scheme=CompressionScheme.SEARCH,
        )
        expected = [bent_timer(PLAYER_TIMER_TABLE[frame.pitch], frame.timer_offset) for frame in test_case.frames]
        assert sounded_dividers(song)[: len(expected)] == expected


PULSE1_BEND: Final[int] = plane_index(ChannelName.PULSE1, PlaneRole.BEND)


class TestABentSongComingRound:
    """A song returning to a tick re-enters each bend plane past the flags played before it."""

    LOOP_TICK: Final[int] = 5
    ROUNDS: Final[int] = 3

    @pytest.fixture
    def repeating(self) -> Song:
        frames = [
            PulseInstruction(
                on=True, pitch=PLAYER_REFERENCE_PITCH, volume=PLAYER_FULL_VOLUME, duty_cycle=0, detune=bend
            )
            for bend in VIBRATO * 2
        ]
        streams = streams_from_instructions({ChannelName.PULSE1: frames}, PLAYER_TIMER_TABLE)
        return player_song(streams, NTSC_RATE, loop_tick=self.LOOP_TICK)

    def test_the_loop_tick_falls_after_flagged_ticks(self, repeating: Song) -> None:
        planes = decode_planes(repeating.planes)
        assert planes.positions(self.LOOP_TICK)[PULSE1_BEND] > 0

    def test_the_console_writes_what_the_model_states_across_its_loops(self, repeating: Song) -> None:
        calls = play_calls_reaching(repeating, self.ROUNDS * repeating.ticks)
        trace = captured_trace_over(repeating, sample_information(SONG_NAME), calls)
        assert trace == RegisterTrace.from_song(repeating, calls)
