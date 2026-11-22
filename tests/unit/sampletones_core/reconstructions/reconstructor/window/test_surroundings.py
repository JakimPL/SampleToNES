from typing import Final, List, Optional

import numpy as np
import pytest

from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.window.profiles import FrameProfiles
from sampletones_core.reconstructions.reconstructor.window.surroundings import (
    ChannelLine,
    NoteKey,
    surroundings,
)

HELD: Final[NoteKey] = (57, 0)
NEXT: Final[NoteKey] = (60, 0)
OTHER: Final[NoteKey] = (64, 0)
POWER: Final[np.ndarray] = np.array([4.0, 1.0])
HELD_NOTE: Final[PulseInstruction] = PulseInstruction(on=True, pitch=57, volume=12, duty_cycle=0)
QUIET: Final[PulseInstruction] = PulseInstruction.null_instruction()
FRAMES: Final[int] = 9
MIDDLE: Final[int] = 4
SPREAD: Final[np.ndarray] = np.array([0.1, 0.2, 0.4, 0.2, 0.1])
PROFILES: Final[FrameProfiles] = FrameProfiles(
    amplitude=np.stack([SPREAD, np.array([0.0, 0.0, 1.0, 0.0, 0.0])], axis=1),
    energy=np.stack([np.square(SPREAD) / np.square(SPREAD).sum(), np.array([0.0, 0.0, 1.0, 0.0, 0.0])], axis=1),
    reach=2,
)


def _run(key: Optional[NoteKey], frames: int) -> List[Optional[NoteKey]]:
    return [key for _ in range(frames)]


def _line(keys: List[Optional[NoteKey]], *, coherent: bool = True) -> ChannelLine:
    powers = np.stack([POWER if key is not None else np.zeros_like(POWER) for key in keys])
    instructions = [HELD_NOTE if key is not None else QUIET for key in keys]
    return ChannelLine(keys=list(keys), powers=powers, instructions=list(instructions), coherent=coherent)


class TestAHeldNote:
    def test_a_note_held_through_the_frame_reaches_it_as_a_steady_note_does(self) -> None:
        around = surroundings(_line(_run(HELD, FRAMES)), MIDDLE, PROFILES)

        heard = around.heard([HELD], POWER[None, :])[0]

        assert around.leak + heard == pytest.approx(POWER)

    def test_a_note_held_up_to_the_frame_leaves_its_tail_in_the_frame(self) -> None:
        keys = _run(HELD, MIDDLE) + _run(None, FRAMES - MIDDLE)

        around = surroundings(_line(keys), MIDDLE, PROFILES)

        tail = SPREAD[0] + SPREAD[1]
        assert around.leak == pytest.approx(np.array([tail**2 * POWER[0], 0.0]))
        assert around.heard([None], np.zeros((1, 2)))[0] == pytest.approx(np.zeros(2))

    def test_a_note_starting_at_the_frame_extends_the_note_held_from_it(self) -> None:
        keys = _run(HELD, MIDDLE) + _run(NEXT, FRAMES - MIDDLE)
        around = surroundings(_line(keys), MIDDLE, PROFILES)

        started = around.heard([NEXT], POWER[None, :])[0]

        held_on = (SPREAD[2] + SPREAD[3] + SPREAD[4]) ** 2 * POWER[0]
        tail = (SPREAD[0] + SPREAD[1]) ** 2 * POWER[0]
        assert around.leak + started == pytest.approx(np.array([held_on + tail, POWER[1]]))

    def test_a_note_unlike_both_neighbors_reaches_the_frame_by_its_own_share_alone(self) -> None:
        keys = _run(HELD, MIDDLE) + _run(OTHER, 1) + _run(NEXT, FRAMES - MIDDLE - 1)
        around = surroundings(_line(keys), MIDDLE, PROFILES)

        heard = around.heard([OTHER], POWER[None, :])[0]

        assert heard == pytest.approx(np.square(PROFILES.own_amplitude) * POWER)
        assert not around.extends(OTHER)
        assert around.extends(HELD) and around.extends(NEXT)

    @pytest.mark.parametrize("key", [HELD, NEXT, OTHER], ids=["before", "after", "unlike"])
    def test_a_fit_reads_a_row_at_its_neighbors_level_as_the_frame_hears_it(self, key: NoteKey) -> None:
        keys = _run(HELD, MIDDLE) + _run(None, 1) + _run(NEXT, FRAMES - MIDDLE - 1)
        around = surroundings(_line(keys), MIDDLE, PROFILES)

        assert around.gains([key])[0] * POWER == pytest.approx(around.heard([key], POWER[None, :])[0])

    def test_a_window_reaching_before_the_line_s_start_reads_silence_there(self) -> None:
        around = surroundings(_line(_run(HELD, FRAMES)), 0, PROFILES)

        heard = around.heard([HELD], POWER[None, :])[0]

        from_start = (SPREAD[2] + SPREAD[3] + SPREAD[4]) ** 2
        assert around.leak + heard == pytest.approx(np.array([from_start * POWER[0], POWER[1]]))


class TestNoise:
    def test_noise_held_through_the_frame_reaches_it_whole(self) -> None:
        around = surroundings(_line(_run(HELD, FRAMES), coherent=False), MIDDLE, PROFILES)

        heard = around.heard([HELD], POWER[None, :])[0]

        assert around.leak + heard == pytest.approx(POWER)
        assert around.before is None and around.after is None

    def test_a_noise_row_reaches_the_frame_by_its_share_of_squared_weight(self) -> None:
        around = surroundings(_line(_run(None, FRAMES), coherent=False), MIDDLE, PROFILES)

        assert around.heard([HELD], POWER[None, :])[0] == pytest.approx(PROFILES.own_energy * POWER)
        assert around.leak == pytest.approx(np.zeros(2))


class TestSettlingAFrame:
    def test_a_settled_frame_is_heard_by_the_frames_after_it(self) -> None:
        line = _line(_run(HELD, MIDDLE) + _run(None, FRAMES - MIDDLE))

        line.settle(MIDDLE, HELD, POWER, HELD_NOTE)

        around = surroundings(line, MIDDLE + 1, PROFILES)
        assert around.before is not None and around.before.key == HELD
        assert around.extends(HELD)
        assert line.instructions[MIDDLE] == HELD_NOTE
