from dataclasses import dataclass
from typing import AbstractSet, Final, FrozenSet, List, Sequence

import pytest

from sampletones_core.constants.algorithm import AUTHORED_STEM_ID, RESTING_STEM_ID
from sampletones_core.instructions import InstructionUnion, PulseInstruction
from sampletones_core.reconstructions.reconstruction.stems.ownership import (
    OwnerRun,
    carried_edit,
    owner_runs,
    writes_reach,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

STEM_A: Final[int] = 0
STEM_B: Final[int] = 1
EVERY_STEM: Final[FrozenSet[int]] = frozenset({STEM_A, STEM_B})
NOTHING_HEARD: Final[FrozenSet[int]] = frozenset()


def _pulse(pitch: int) -> PulseInstruction:
    return PulseInstruction(on=True, pitch=pitch, volume=8, duty_cycle=0)


def _silence() -> PulseInstruction:
    return PulseInstruction.null_instruction()


class TestTheOwnerAFrameLeavesAnEditWith(BaseTestSuite):
    """A frame's owner follows from the frame it was and the frame it becomes.

    Rest and silence name the same frames, so the three outcomes below cover every frame:
    one that sounds through the edit keeps its owner, one the edit quiets rests, and one the
    edit brings into play is the reader's own.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        owner: int
        previous: InstructionUnion
        proposed: InstructionUnion
        expected: int

    test_cases = (
        TestCase(
            label="a recording's frame edited to another note keeps its recording",
            owner=STEM_A,
            previous=_pulse(60),
            proposed=_pulse(64),
            expected=STEM_A,
        ),
        TestCase(
            label="a recording's frame edited silent rests",
            owner=STEM_A,
            previous=_pulse(60),
            proposed=_silence(),
            expected=RESTING_STEM_ID,
        ),
        TestCase(
            label="a resting frame edited into play is the reader's own",
            owner=RESTING_STEM_ID,
            previous=_silence(),
            proposed=_pulse(60),
            expected=AUTHORED_STEM_ID,
        ),
        TestCase(
            label="a resting frame edited silent rests on",
            owner=RESTING_STEM_ID,
            previous=_silence(),
            proposed=_silence(),
            expected=RESTING_STEM_ID,
        ),
        TestCase(
            label="a frame the reader wrote keeps the reader through another edit",
            owner=AUTHORED_STEM_ID,
            previous=_pulse(60),
            proposed=_pulse(64),
            expected=AUTHORED_STEM_ID,
        ),
        TestCase(
            label="a frame the reader wrote rests once the reader quiets it",
            owner=AUTHORED_STEM_ID,
            previous=_pulse(60),
            proposed=_silence(),
            expected=RESTING_STEM_ID,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_owner_the_frame_carries(self, test_case: TestCase) -> None:
        carried = carried_edit(
            [test_case.previous],
            [test_case.owner],
            [test_case.proposed],
            heard=EVERY_STEM,
        )

        assert carried.stem_ids == [test_case.expected]


class TestAnEditThatChangesTheFrameCount:
    def test_frames_written_past_the_end_are_the_readers_own(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [_pulse(60), _pulse(62)], heard=EVERY_STEM)

        assert carried.stem_ids == [STEM_A, AUTHORED_STEM_ID]

    def test_a_silent_frame_written_past_the_end_rests(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [_pulse(60), _silence()], heard=EVERY_STEM)

        assert carried.stem_ids == [STEM_A, RESTING_STEM_ID]

    def test_frames_the_edit_drops_take_their_ownership_along(self) -> None:
        carried = carried_edit(
            [_pulse(60), _pulse(62)],
            [STEM_A, STEM_B],
            [_pulse(60)],
            heard=EVERY_STEM,
        )

        assert carried.stem_ids == [STEM_A]
        assert carried.instructions == [_pulse(60)]

    def test_a_frame_dropped_outside_the_scope_keeps_playing(self) -> None:
        carried = carried_edit(
            [_pulse(60), _pulse(62), _pulse(64)],
            [STEM_A, STEM_B, STEM_B],
            [_pulse(70)],
            heard=frozenset({STEM_A}),
        )

        assert carried.instructions == [_pulse(70), _pulse(62), _pulse(64)]
        assert carried.stem_ids == [STEM_A, STEM_B, STEM_B]

    def test_a_frame_the_scope_reached_rests_where_the_stream_runs_on_without_it(self) -> None:
        carried = carried_edit(
            [_pulse(60), _pulse(62), _pulse(64)],
            [STEM_A, STEM_A, STEM_B],
            [],
            heard=frozenset({STEM_A}),
        )

        assert carried.instructions == [_silence(), _silence(), _pulse(64)]
        assert carried.stem_ids == [RESTING_STEM_ID, RESTING_STEM_ID, STEM_B]

    def test_a_channel_shortened_within_its_scope_runs_exactly_as_far_as_the_edit_states(self) -> None:
        carried = carried_edit(
            [_pulse(60), _pulse(62), _pulse(64)],
            [STEM_A, STEM_B, STEM_A],
            [_pulse(70)],
            heard=EVERY_STEM,
        )

        assert carried.instructions == [_pulse(70)]
        assert carried.stem_ids == [STEM_A]

    def test_a_resting_frame_past_the_edit_goes_whatever_is_heard(self) -> None:
        carried = carried_edit(
            [_pulse(60), _silence()],
            [STEM_A, RESTING_STEM_ID],
            [_pulse(70)],
            heard=NOTHING_HEARD,
        )

        assert carried.instructions == [_pulse(60)]
        assert carried.stem_ids == [STEM_A]

    def test_a_channel_edited_down_to_no_frame_carries_no_ownership(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [], heard=EVERY_STEM)

        assert carried.instructions == []
        assert carried.stem_ids == []

    def test_a_channel_edited_down_to_no_frame_outside_the_scope_stands_whole(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [], heard=NOTHING_HEARD)

        assert carried.instructions == [_pulse(60)]
        assert carried.stem_ids == [STEM_A]

    def test_a_channel_written_back_into_play_comes_back_the_readers_own(self) -> None:
        carried = carried_edit([], [], [_pulse(60), _silence()], heard=EVERY_STEM)

        assert carried.stem_ids == [AUTHORED_STEM_ID, RESTING_STEM_ID]


class TestTheScopeAnEditWritesIn:
    """A frame accepts a gesture where its owner is heard, where it rests, and where it is the reader's.

    Every other frame reads as it stands, which is what lets one recording's part be shaped
    while the recordings beside it carry on.
    """

    def test_a_frame_of_a_recording_the_reader_hears_takes_the_edit(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [_pulse(64)], heard=frozenset({STEM_A}))

        assert carried.instructions == [_pulse(64)]
        assert carried.stem_ids == [STEM_A]

    def test_a_frame_of_a_recording_the_reader_left_out_stands_as_it_is(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [_pulse(64)], heard=frozenset({STEM_B}))

        assert carried.instructions == [_pulse(60)]
        assert carried.stem_ids == [STEM_A]

    def test_a_resting_frame_takes_the_edit_whatever_is_heard(self) -> None:
        carried = carried_edit([_silence()], [RESTING_STEM_ID], [_pulse(60)], heard=NOTHING_HEARD)

        assert carried.instructions == [_pulse(60)]
        assert carried.stem_ids == [AUTHORED_STEM_ID]

    def test_a_frame_the_reader_wrote_takes_the_edit_whatever_is_heard(self) -> None:
        carried = carried_edit([_pulse(60)], [AUTHORED_STEM_ID], [_pulse(64)], heard=NOTHING_HEARD)

        assert carried.instructions == [_pulse(64)]
        assert carried.stem_ids == [AUTHORED_STEM_ID]

    def test_a_frame_written_past_the_end_takes_the_edit_whatever_is_heard(self) -> None:
        carried = carried_edit([_pulse(60)], [STEM_A], [_pulse(60), _pulse(62)], heard=NOTHING_HEARD)

        assert carried.instructions == [_pulse(60), _pulse(62)]
        assert carried.stem_ids == [STEM_A, AUTHORED_STEM_ID]

    def test_an_edit_the_scope_refuses_throughout_leaves_the_channel_as_it_stood(self) -> None:
        previous = [_pulse(60), _pulse(62)]
        stem_ids = [STEM_A, STEM_B]

        carried = carried_edit(previous, stem_ids, [_silence(), _silence()], heard=NOTHING_HEARD)

        assert carried.instructions == previous
        assert carried.stem_ids == stem_ids

    def test_an_edit_reaches_one_recordings_frames_and_leaves_the_others(self) -> None:
        previous = [_pulse(60), _pulse(62), _silence()]
        stem_ids = [STEM_A, STEM_B, RESTING_STEM_ID]

        carried = carried_edit(
            previous,
            stem_ids,
            [_pulse(70), _pulse(70), _pulse(70)],
            heard=frozenset({STEM_A}),
        )

        assert carried.instructions == [_pulse(70), _pulse(62), _pulse(70)]
        assert carried.stem_ids == [STEM_A, STEM_B, AUTHORED_STEM_ID]


class TestTheFramesAnEditMayWrite:
    @staticmethod
    def _reach(stem_ids: Sequence[int], heard: AbstractSet[int]) -> List[bool]:
        return writes_reach(stem_ids, heard)

    def test_every_frame_is_reachable_while_every_recording_is_heard(self) -> None:
        assert self._reach([STEM_A, STEM_B, RESTING_STEM_ID], EVERY_STEM) == [True, True, True]

    def test_a_recording_left_out_holds_its_frames_back(self) -> None:
        assert self._reach([STEM_A, STEM_B], frozenset({STEM_B})) == [False, True]

    def test_resting_and_authored_frames_stay_reachable(self) -> None:
        assert self._reach([RESTING_STEM_ID, AUTHORED_STEM_ID], NOTHING_HEARD) == [True, True]


class TestTheStretchesAChannelDividesInto:
    """A reader follows a recording by the stretches it holds, so the record reads as runs."""

    def test_a_run_gathers_the_frames_one_recording_holds_in_a_row(self) -> None:
        runs = owner_runs([STEM_A, STEM_A, STEM_B])

        assert runs == [OwnerRun(start=0, end=2, stem_id=STEM_A), OwnerRun(start=2, end=3, stem_id=STEM_B)]

    def test_a_recording_coming_back_takes_a_run_of_its_own(self) -> None:
        runs = owner_runs([STEM_A, STEM_B, STEM_A])

        assert [run.stem_id for run in runs] == [STEM_A, STEM_B, STEM_A]

    def test_resting_and_authored_frames_take_runs_like_any_other(self) -> None:
        runs = owner_runs([RESTING_STEM_ID, RESTING_STEM_ID, AUTHORED_STEM_ID])

        assert runs == [
            OwnerRun(start=0, end=2, stem_id=RESTING_STEM_ID),
            OwnerRun(start=2, end=3, stem_id=AUTHORED_STEM_ID),
        ]

    def test_the_runs_cover_the_channel_end_to_end_without_overlapping(self) -> None:
        stem_ids = [STEM_A, STEM_A, RESTING_STEM_ID, STEM_B, STEM_B, STEM_B]

        runs = owner_runs(stem_ids)

        assert runs[0].start == 0
        assert runs[-1].end == len(stem_ids)
        assert all(before.end == after.start for before, after in zip(runs, runs[1:]))

    def test_a_channel_standing_by_divides_into_nothing(self) -> None:
        assert owner_runs([]) == []
