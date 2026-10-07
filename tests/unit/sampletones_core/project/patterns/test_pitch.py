from dataclasses import dataclass
from typing import Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import (
    MAX_PERIOD,
    MAX_PITCH,
    MAX_TRANSPOSE,
    MIN_PLAYED_PITCH,
    MIN_TRANSPOSE,
    NUM_PERIODS,
)
from sampletones_core.project.patterns.pitch import (
    Note,
    RowPitch,
    Step,
    clamped_note,
    clamped_step,
    note_for_channel,
    played_note,
    shifted_pitch,
    sounded_pitch,
    step_of,
)
from sampletones_core.project.patterns.row import Row
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestStepOf(BaseTestSuite):
    """A step states its offset outright, and a note is measured from the voice's reference."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: int
        pitch: RowPitch
        reference: int

    test_cases: Tuple["TestStepOf.TestCase", ...] = (
        TestCase(label="a step", pitch=Step(value=5), reference=60, expected=5),
        TestCase(label="a note above the reference", pitch=Note(value=67), reference=60, expected=7),
        TestCase(label="a note at the reference", pitch=Note(value=60), reference=60, expected=0),
        TestCase(label="a period below the reference", pitch=Note(value=3), reference=9, expected=-6),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_step_a_pitch_asks_for(self, test_case: TestCase) -> None:
        assert step_of(test_case.pitch, reference=test_case.reference) == test_case.expected


class TestSoundedPitch(BaseTestSuite):
    """Where a voice sounds: held within the notes a tonal channel plays, walked around the periods on noise."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: int
        channel: ChannelName
        pitch: RowPitch
        reference: int

    test_cases: Tuple["TestSoundedPitch.TestCase", ...] = (
        TestCase(
            label="a note sounds where it says",
            channel=ChannelName.PULSE1,
            pitch=Note(value=67),
            reference=60,
            expected=67,
        ),
        TestCase(
            label="a note below the lowest played note is held there",
            channel=ChannelName.PULSE1,
            pitch=Note(value=20),
            reference=60,
            expected=MIN_PLAYED_PITCH,
        ),
        TestCase(
            label="a step past the highest note is held there",
            channel=ChannelName.TRIANGLE,
            pitch=Step(value=MAX_TRANSPOSE),
            reference=MAX_PITCH,
            expected=MAX_PITCH,
        ),
        TestCase(
            label="a step on noise walks around the sixteen",
            channel=ChannelName.NOISE,
            pitch=Step(value=14),
            reference=5,
            expected=(5 + 14) % NUM_PERIODS,
        ),
        TestCase(
            label="a period on noise sounds where it says",
            channel=ChannelName.NOISE,
            pitch=Note(value=3),
            reference=9,
            expected=3,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_where_the_voice_sounds(self, test_case: TestCase) -> None:
        assert sounded_pitch(test_case.channel, test_case.pitch, reference=test_case.reference) == test_case.expected


class TestClampedPitches(BaseTestSuite):
    """A note is held inside what the channel plays, and a step inside what a row accepts."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: RowPitch
        channel: ChannelName
        value: int

    test_cases: Tuple["TestClampedPitches.TestCase", ...] = (
        TestCase(
            label="a low pitch rises to C-0",
            channel=ChannelName.PULSE1,
            value=20,
            expected=Note(value=MIN_PLAYED_PITCH),
        ),
        TestCase(
            label="a high pitch falls to B-7", channel=ChannelName.PULSE2, value=200, expected=Note(value=MAX_PITCH)
        ),
        TestCase(
            label="a pitch on noise falls to the last period",
            channel=ChannelName.NOISE,
            value=20,
            expected=Note(value=MAX_PERIOD),
        ),
        TestCase(
            label="a negative period rises to the first", channel=ChannelName.NOISE, value=-1, expected=Note(value=0)
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_note_a_channel_keeps(self, test_case: TestCase) -> None:
        assert clamped_note(test_case.channel, test_case.value) == test_case.expected

    @pytest.mark.parametrize(("value", "expected"), [(100, MAX_TRANSPOSE), (-100, MIN_TRANSPOSE), (5, 5)])
    def test_the_step_a_row_keeps(self, value: int, expected: int) -> None:
        assert clamped_step(value) == Step(value=expected)


class TestNoteForChannel(BaseTestSuite):
    """A piano key names a pitch; a tonal channel takes it as its note, and noise as the period it names."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: int
        channel: ChannelName
        pitch: int

    test_cases: Tuple["TestNoteForChannel.TestCase", ...] = (
        TestCase(label="a pitch within the range stands", channel=ChannelName.PULSE1, pitch=60, expected=60),
        TestCase(label="a pitch past B-7 is held at it", channel=ChannelName.TRIANGLE, pitch=131, expected=MAX_PITCH),
        TestCase(label="a C names the first period", channel=ChannelName.NOISE, pitch=48, expected=0),
        TestCase(label="a D an octave up walks the periods round", channel=ChannelName.NOISE, pitch=62, expected=14),
        TestCase(
            label="a period lies where its pitch does", channel=ChannelName.NOISE, pitch=MAX_PERIOD, expected=MAX_PERIOD
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_note_the_channel_takes(self, test_case: TestCase) -> None:
        assert note_for_channel(test_case.channel, test_case.pitch) == Note(value=test_case.expected)

    @pytest.mark.parametrize(("pitch", "expected"), [(131, MAX_PITCH), (20, MIN_PLAYED_PITCH), (60, 60)])
    def test_a_played_note_is_held_within_the_notes_a_channel_plays(self, pitch: int, expected: int) -> None:
        assert played_note(pitch) == Note(value=expected)


class TestShiftedPitch(BaseTestSuite):
    """A nudge moves a pitch on its own face and stops at the face's ends."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: RowPitch
        pitch: RowPitch
        delta: int
        channel: ChannelName = ChannelName.PULSE1

    test_cases: Tuple["TestShiftedPitch.TestCase", ...] = (
        TestCase(label="a step moves", pitch=Step(value=1), delta=12, expected=Step(value=13)),
        TestCase(
            label="a step stops at the top",
            pitch=Step(value=MAX_TRANSPOSE - 1),
            delta=5,
            expected=Step(value=MAX_TRANSPOSE),
        ),
        TestCase(label="a note moves", pitch=Note(value=60), delta=12, expected=Note(value=72)),
        TestCase(label="a note stops at B-7", pitch=Note(value=MAX_PITCH - 1), delta=5, expected=Note(value=MAX_PITCH)),
        TestCase(
            label="a note stops at C-0",
            pitch=Note(value=MIN_PLAYED_PITCH),
            delta=-1,
            expected=Note(value=MIN_PLAYED_PITCH),
        ),
        TestCase(
            label="a period stops at the last",
            channel=ChannelName.NOISE,
            pitch=Note(value=14),
            delta=5,
            expected=Note(value=MAX_PERIOD),
        ),
        TestCase(
            label="a period stops at the first",
            channel=ChannelName.NOISE,
            pitch=Note(value=0),
            delta=-1,
            expected=Note(value=0),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_where_the_nudge_lands(self, test_case: TestCase) -> None:
        assert shifted_pitch(test_case.pitch, test_case.delta, test_case.channel) == test_case.expected


class TestThePitchModel:
    """A pitch stores its face beside its value, so a row reads back exactly what was written."""

    @pytest.mark.parametrize("pitch", [Note(value=60), Step(value=-3), Step(value=0)])
    def test_a_row_round_trips_its_pitch(self, pitch: RowPitch) -> None:
        row = Row(pitch=pitch)

        assert Row.model_validate(row.model_dump()) == row
        assert Row.model_validate_json(row.model_dump_json()).pitch == pitch

    def test_a_step_reads_from_its_stored_shape(self) -> None:
        assert Row.model_validate({"pitch": {"kind": "step", "value": 3}}).pitch == Step(value=3)

    def test_a_note_reads_from_its_stored_shape(self) -> None:
        assert Row.model_validate({"pitch": {"kind": "note", "value": 61}}).pitch == Note(value=61)

    @pytest.mark.parametrize(
        "stored",
        [
            {"kind": "bend", "value": 3},
            {"kind": "note", "value": MAX_PITCH + 1},
            {"kind": "step", "value": MAX_TRANSPOSE + 1},
        ],
    )
    def test_a_shape_the_union_lacks_is_refused(self, stored: object) -> None:
        with pytest.raises(ValidationError):
            Row.model_validate({"pitch": stored})

    def test_the_two_faces_compare_apart(self) -> None:
        assert Note(value=5) != Step(value=5)
