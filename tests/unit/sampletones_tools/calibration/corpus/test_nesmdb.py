from dataclasses import dataclass
from typing import Dict, Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_tools.calibration.corpus.midi import read_midi
from sampletones_tools.calibration.corpus.nesmdb import INITIAL_DUTY_CYCLE, nesmdb_frames
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..midifiles import midi_file, nesmdb_piece, ticks, track

RATE: Final[int] = 60
QUARTER_FRAME_TICKS: Final[int] = ticks(0.25 / RATE)
SECOND_TICKS: Final[int] = ticks(1.0)
NOTE_ON: Final[int] = 0x90
NOTE_OFF: Final[int] = 0x80
CONTROL_CHANGE: Final[int] = 0xB0
VOLUME: Final[int] = 11
TIMBRE: Final[int] = 12
VELOCITY: Final[int] = 10
A4: Final[int] = 69


def _frames(piece: bytes, *, start_frame: int, frames: int) -> Dict[ChannelName, List[InstructionUnion]]:
    return nesmdb_frames(read_midi(piece), start_frame=start_frame, frames=frames, rate=RATE)


@pytest.fixture(name="frames", scope="module")
def frames_fixture() -> Dict[ChannelName, List[InstructionUnion]]:
    return _frames(nesmdb_piece(), start_frame=0, frames=RATE)


class TestNesmdbFrames:
    def test_a_pulse_starts_at_its_velocity_and_moves_with_the_volume_controller(
        self,
        frames: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        pulse = frames[ChannelName.PULSE1]

        assert pulse[0] == PulseInstruction(on=True, pitch=69, volume=12, duty_cycle=1)
        assert pulse[RATE - 1] == PulseInstruction(on=True, pitch=69, volume=6, duty_cycle=1)

    def test_the_triangle_plays_an_octave_above_the_pitch_it_sounds(
        self,
        frames: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        assert frames[ChannelName.TRIANGLE][0] == TriangleInstruction(on=True, pitch=57)

    def test_the_noise_counts_its_periods_from_the_lowest_and_takes_its_mode(
        self,
        frames: Dict[ChannelName, List[InstructionUnion]],
    ) -> None:
        noise = frames[ChannelName.NOISE]

        assert noise[0] == NoiseInstruction(on=True, period=3, volume=9, short=True)
        assert not noise[RATE // 2].on

    def test_a_window_starts_where_it_is_asked_to(self) -> None:
        late = _frames(nesmdb_piece(), start_frame=RATE // 2, frames=2)

        pulse = late[ChannelName.PULSE1][0]
        assert isinstance(pulse, PulseInstruction) and pulse.volume == 6

    def test_a_window_past_the_piece_holds_every_channel_silent(self) -> None:
        late = _frames(nesmdb_piece(), start_frame=2 * RATE, frames=3)

        assert set(late) == {ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE}
        assert not any(frame.on for stream in late.values() for frame in stream)

    def test_a_track_of_another_name_is_left_out(self) -> None:
        piece = midi_file(
            [
                track("p2", [(0, bytes([NOTE_ON, A4, VELOCITY])), (ticks(1.0), bytes([NOTE_OFF, A4, 0]))], tempo=True),
                track("dpcm", [(0, bytes([NOTE_ON, A4, VELOCITY])), (ticks(1.0), bytes([NOTE_OFF, A4, 0]))]),
            ]
        )

        assert set(_frames(piece, start_frame=0, frames=2)) == {ChannelName.PULSE2}


class TestFrameEdges(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        start: int
        end: int
        frame: int

    test_cases = (
        TestCase(start=QUARTER_FRAME_TICKS, end=SECOND_TICKS, frame=0, expected=True, label="starting a quarter in"),
        TestCase(
            start=3 * QUARTER_FRAME_TICKS, end=SECOND_TICKS, frame=0, expected=False, label="starting three quarters in"
        ),
        TestCase(
            start=0, end=SECOND_TICKS + QUARTER_FRAME_TICKS, frame=RATE, expected=False, label="ending a quarter in"
        ),
        TestCase(
            start=0,
            end=SECOND_TICKS + 3 * QUARTER_FRAME_TICKS,
            frame=RATE,
            expected=True,
            label="ending three quarters in",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_frame_plays_the_note_sounding_at_its_middle(self, test_case: TestCase) -> None:
        messages = [
            (test_case.start, bytes([NOTE_ON, A4, VELOCITY])),
            (test_case.end - test_case.start, bytes([NOTE_OFF, A4, 0])),
        ]

        frame = _frames(midi_file([track("p1", messages, tempo=True)]), start_frame=test_case.frame, frames=1)

        assert frame[ChannelName.PULSE1][0].on is test_case.expected


class TestVolumeAndTimbre:
    def test_a_pulse_set_no_duty_cycle_plays_the_initial_one(self) -> None:
        piece = midi_file(
            [track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (ticks(1.0), bytes([NOTE_OFF, A4, 0]))], tempo=True)]
        )

        frame = _frames(piece, start_frame=0, frames=1)[ChannelName.PULSE1][0]

        assert frame == PulseInstruction(on=True, pitch=A4, volume=VELOCITY, duty_cycle=INITIAL_DUTY_CYCLE)

    def test_a_volume_set_to_zero_silences_the_note(self) -> None:
        piece = midi_file(
            [
                track(
                    "p1",
                    [
                        (0, bytes([NOTE_ON, A4, VELOCITY])),
                        (ticks(0.5), bytes([CONTROL_CHANGE, VOLUME, 0])),
                        (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
                    ],
                    tempo=True,
                )
            ]
        )

        pulse = _frames(piece, start_frame=0, frames=RATE)[ChannelName.PULSE1]

        assert pulse[0].on and not pulse[RATE - 1].on

    def test_a_volume_set_before_the_note_starts_leaves_its_velocity(self) -> None:
        piece = midi_file(
            [
                track(
                    "p1",
                    [
                        (0, bytes([CONTROL_CHANGE, VOLUME, 3])),
                        (ticks(0.5), bytes([NOTE_ON, A4, VELOCITY])),
                        (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
                    ],
                    tempo=True,
                )
            ]
        )

        pulse = _frames(piece, start_frame=RATE // 2, frames=RATE // 2)[ChannelName.PULSE1]

        assert {frame.volume for frame in pulse if isinstance(frame, PulseInstruction)} == {VELOCITY}

    @pytest.mark.parametrize(("note", "period"), [(16, 0), (1, MAX_PERIOD)], ids=["highest", "lowest"])
    def test_the_noise_note_counts_down_from_the_highest_period(self, note: int, period: int) -> None:
        piece = midi_file(
            [track("no", [(0, bytes([NOTE_ON, note, VELOCITY])), (ticks(1.0), bytes([NOTE_OFF, note, 0]))], tempo=True)]
        )

        frame = _frames(piece, start_frame=0, frames=1)[ChannelName.NOISE][0]

        assert frame == NoiseInstruction(on=True, period=period, volume=VELOCITY, short=False)

    def test_the_timbre_holds_across_notes(self) -> None:
        piece = midi_file(
            [
                track(
                    "p1",
                    [
                        (0, bytes([CONTROL_CHANGE, TIMBRE, 3])),
                        (0, bytes([NOTE_ON, A4, VELOCITY])),
                        (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
                        (0, bytes([NOTE_ON, A4 + 1, VELOCITY])),
                        (ticks(0.5), bytes([NOTE_OFF, A4 + 1, 0])),
                    ],
                    tempo=True,
                )
            ]
        )

        pulse = _frames(piece, start_frame=0, frames=RATE)[ChannelName.PULSE1]

        assert {frame.duty_cycle for frame in pulse if isinstance(frame, PulseInstruction)} == {3}
        assert {frame.pitch for frame in pulse} == {A4, A4 + 1}
