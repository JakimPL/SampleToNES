from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from sampletones_core.project.patterns.row import Row
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


def _note_on() -> NoteOn:
    return NoteOn(voice_id="abc123")


class TestNoteOn:
    def test_is_frozen(self) -> None:
        note_on = _note_on()
        with pytest.raises(ValidationError):
            note_on.voice_id = "other"  # type: ignore[misc]

    def test_value_equality_and_hash(self) -> None:
        first = _note_on()
        second = _note_on()
        assert first == second
        assert hash(first) == hash(second)

    def test_distinct_voices_differ(self) -> None:
        assert NoteOn(voice_id="abc") != NoteOn(voice_id="def")

    def test_names_the_voice_alone(self) -> None:
        with pytest.raises(ValidationError):
            NoteOn.model_validate({"voice_id": "abc", "channel_name": "triangle"})

    def test_round_trip(self) -> None:
        note_on = _note_on()
        restored = NoteOn.model_validate(note_on.model_dump())
        assert restored == note_on


class TestRowDefaults:
    def test_empty_row(self) -> None:
        row = Row()
        assert row.transpose is None
        assert row.command is None
        assert row.volume is None

    def test_is_frozen(self) -> None:
        row = Row(transpose=12)
        with pytest.raises(ValidationError):
            row.transpose = 13  # type: ignore[misc]


class TestRowSerialization(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Row

        @property
        def label(self) -> str:
            return f"transpose={self.expected.transpose}_command={self.expected.command is not None}"

    test_cases = (
        TestCase(expected=Row()),
        TestCase(expected=Row(transpose=0, volume=15)),
        TestCase(expected=Row(transpose=12, command=_note_on(), volume=8)),
        TestCase(expected=Row(command=NoteOff())),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_round_trip(self, test_case: TestCase) -> None:
        row = test_case.expected
        assert Row.model_validate(row.model_dump()) == row
        assert Row.model_validate_json(row.model_dump_json()) == row
