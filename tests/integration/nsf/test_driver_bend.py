from dataclasses import dataclass
from typing import Final, List, Self, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_player.song import Song
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.registers import PULSE1_TIMER_HIGH, TIMER_HIGH_SHIFT
from sampletones_player.trace.trace import RegisterTrace
from tests.integration.nsf.console.instructions import channel_values, timer_value
from tests.integration.nsf.console.machine import register_file
from tests.integration.nsf.console.session import captured_trace, play_calls_covering
from tests.integration.nsf.exports import exported_information
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.player import PLAYER_PITCHES, bent_song

NTSC_RATE: Final[int] = 60
SONG_NAME: Final[str] = "bend"

MIDRANGE_INDEX: Final[int] = 33
BOUNDARY_INDEX: Final[int] = 17
WIDEST_RESIDUAL: Final[int] = 57
TIMER_LOW_INDEX: Final[int] = 1
TIMER_HIGH_INDEX: Final[int] = 2


def sounded_dividers(song: Song) -> List[int]:
    """The divider the console leaves on the first pulse channel after each tick it sounds.

    Args:
        song: The song to export and run.

    Returns:
        List[int]: One divider per tick the song covers, in order.
    """
    trace = captured_trace(song, exported_information(SONG_NAME))
    dividers = []
    for registers in register_file(trace):
        values = channel_values(registers, ChannelName.PULSE1)
        dividers.append(timer_value(values[TIMER_LOW_INDEX], values[TIMER_HIGH_INDEX]))

    return dividers[: song.planes.ticks]


class TestTheDriverSoundsTheDividerABendPlaneNames(BaseTestSuite):
    """The assembled 6502 driver run on py65, its timer registers read back tick by tick.

    A plane byte reaches the timer through a sign extension and a sixteen-bit add, which is the
    one piece of arithmetic the driver performs on a song's behalf. These runs state a bend
    outright — the encoders leave the dimension to the note for now — and hold the console to the
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
        trace = captured_trace(song, exported_information(SONG_NAME))
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

        trace = captured_trace(crossing, exported_information(SONG_NAME))
        written = [write for writes in trace.play_calls for write in writes if write.address == PULSE1_TIMER_HIGH]
        assert crossings
        assert len(written) == crossings
