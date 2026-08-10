from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from sampletones_core.project.settings import ProjectSettings
from sampletones_shared.constants.nes import (
    MAX_NES_FREQUENCY,
    MIN_NES_FREQUENCY,
)
from sampletones_shared.constants.project import (
    DEFAULT_FIRST_HIGHLIGHT,
    DEFAULT_SECOND_HIGHLIGHT,
    MAX_HIGHLIGHT,
    MAX_SPEED,
    MAX_TEMPO,
    MIN_HIGHLIGHT,
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

    test_cases = (
        TestCase(
            field="nes_frequency",
            value=MIN_NES_FREQUENCY,
            expected=True,
        ),
        TestCase(
            field="nes_frequency",
            value=MAX_NES_FREQUENCY,
            expected=True,
        ),
        TestCase(
            field="nes_frequency",
            value=MIN_NES_FREQUENCY - 1,
            expected=False,
        ),
        TestCase(
            field="nes_frequency",
            value=MAX_NES_FREQUENCY + 1,
            expected=False,
        ),
        TestCase(
            field="tempo",
            value=MIN_TEMPO,
            expected=True,
        ),
        TestCase(
            field="tempo",
            value=MAX_TEMPO,
            expected=True,
        ),
        TestCase(
            field="tempo",
            value=MIN_TEMPO - 1,
            expected=False,
        ),
        TestCase(
            field="tempo",
            value=MAX_TEMPO + 1,
            expected=False,
        ),
        TestCase(
            field="speed",
            value=MIN_SPEED,
            expected=True,
        ),
        TestCase(
            field="speed",
            value=MAX_SPEED,
            expected=True,
        ),
        TestCase(
            field="speed",
            value=MIN_SPEED - 1,
            expected=False,
        ),
        TestCase(
            field="speed",
            value=MAX_SPEED + 1,
            expected=False,
        ),
        TestCase(
            field="first_highlight",
            value=MIN_HIGHLIGHT,
            expected=True,
        ),
        TestCase(
            field="first_highlight",
            value=MAX_HIGHLIGHT,
            expected=True,
        ),
        TestCase(
            field="first_highlight",
            value=MIN_HIGHLIGHT - 1,
            expected=False,
        ),
        TestCase(
            field="first_highlight",
            value=MAX_HIGHLIGHT + 1,
            expected=False,
        ),
        TestCase(
            field="second_highlight",
            value=MIN_HIGHLIGHT,
            expected=True,
        ),
        TestCase(
            field="second_highlight",
            value=MAX_HIGHLIGHT,
            expected=True,
        ),
        TestCase(
            field="second_highlight",
            value=MIN_HIGHLIGHT - 1,
            expected=False,
        ),
        TestCase(
            field="second_highlight",
            value=MAX_HIGHLIGHT + 1,
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_bounds(self, test_case: TestCase) -> None:
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
        settings = ProjectSettings(tempo=120, speed=4)
        restored = ProjectSettings.model_validate(settings.model_dump())
        assert restored == settings

    def test_highlights_round_trip(self) -> None:
        settings = ProjectSettings(first_highlight=3, second_highlight=12)
        restored = ProjectSettings.model_validate(settings.model_dump())
        assert (restored.first_highlight, restored.second_highlight) == (3, 12)

    def test_settings_without_highlights_load_on_common_time(self) -> None:
        """A project saved before the highlights existed reads as the 4/16 grouping it was played in."""
        document = ProjectSettings(tempo=120).model_dump()
        del document["first_highlight"]
        del document["second_highlight"]

        restored = ProjectSettings.model_validate(document)

        assert (restored.first_highlight, restored.second_highlight) == (
            DEFAULT_FIRST_HIGHLIGHT,
            DEFAULT_SECOND_HIGHLIGHT,
        )

    def test_json_round_trip(self) -> None:
        settings = ProjectSettings(nes_frequency=50)
        restored = ProjectSettings.model_validate_json(settings.model_dump_json())
        assert restored == settings
