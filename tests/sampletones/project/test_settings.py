from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from sampletones_core.constants.general import (
    MAX_CHANGE_RATE,
    MIN_CHANGE_RATE,
)
from sampletones_core.project.settings import ProjectSettings
from sampletones_shared.constants.project import (
    MAX_ROWS_PER_PATTERN,
    MAX_SPEED,
    MAX_TEMPO,
    MIN_ROWS_PER_PATTERN,
    MIN_SPEED,
    MIN_TEMPO,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestBounds(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: bool
        field: str
        value: int

        @property
        def label(self) -> str:
            verdict = "valid" if self.expected else "invalid"
            return f"{self.field}={self.value}_{verdict}"

    test_cases = [
        TestCase(field="change_rate", value=MIN_CHANGE_RATE, expected=True),
        TestCase(field="change_rate", value=MAX_CHANGE_RATE, expected=True),
        TestCase(field="change_rate", value=MIN_CHANGE_RATE - 1, expected=False),
        TestCase(field="change_rate", value=MAX_CHANGE_RATE + 1, expected=False),
        TestCase(field="tempo", value=MIN_TEMPO, expected=True),
        TestCase(field="tempo", value=MAX_TEMPO, expected=True),
        TestCase(field="tempo", value=MIN_TEMPO - 1, expected=False),
        TestCase(field="tempo", value=MAX_TEMPO + 1, expected=False),
        TestCase(field="speed", value=MIN_SPEED, expected=True),
        TestCase(field="speed", value=MAX_SPEED, expected=True),
        TestCase(field="speed", value=MIN_SPEED - 1, expected=False),
        TestCase(field="speed", value=MAX_SPEED + 1, expected=False),
        TestCase(field="rows_per_pattern", value=MIN_ROWS_PER_PATTERN, expected=True),
        TestCase(field="rows_per_pattern", value=MAX_ROWS_PER_PATTERN, expected=True),
        TestCase(field="rows_per_pattern", value=MIN_ROWS_PER_PATTERN - 1, expected=False),
        TestCase(field="rows_per_pattern", value=MAX_ROWS_PER_PATTERN + 1, expected=False),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_bounds(self, test_case: "TestBounds.TestCase") -> None:
        kwargs = {test_case.field: test_case.value}
        if test_case.expected:
            settings = ProjectSettings(**kwargs)
            assert getattr(settings, test_case.field) == test_case.value
        else:
            with pytest.raises(ValidationError):
                ProjectSettings(**kwargs)


class TestMutability:
    def test_assignment_is_validated(self) -> None:
        settings = ProjectSettings()
        settings.tempo = MAX_TEMPO
        assert settings.tempo == MAX_TEMPO

        with pytest.raises(ValidationError):
            settings.tempo = MIN_TEMPO - 1


class TestSerialization:
    def test_round_trip(self) -> None:
        settings = ProjectSettings(tempo=120, speed=4, rows_per_pattern=32)
        restored = ProjectSettings.model_validate(settings.model_dump())
        assert restored == settings

    def test_json_round_trip(self) -> None:
        settings = ProjectSettings(change_rate=50)
        restored = ProjectSettings.model_validate_json(settings.model_dump_json())
        assert restored == settings
