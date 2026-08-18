from dataclasses import dataclass
from fractions import Fraction

import pytest

from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing.rate import RowRate
from sampletones_shared.constants.project import REFERENCE_NES_FREQUENCY, REFERENCE_TEMPO
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestRowRate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Fraction
        tempo: int
        speed: int
        nes_frequency: int

        @property
        def label(self) -> str:
            return f"tempo_{self.tempo}_speed_{self.speed}_at_{self.nes_frequency}hz"

    test_cases = (
        TestCase(
            tempo=REFERENCE_TEMPO,
            speed=6,
            nes_frequency=REFERENCE_NES_FREQUENCY,
            expected=Fraction(6),
        ),
        TestCase(
            tempo=REFERENCE_TEMPO,
            speed=1,
            nes_frequency=REFERENCE_NES_FREQUENCY,
            expected=Fraction(1),
        ),
        TestCase(
            tempo=REFERENCE_TEMPO,
            speed=31,
            nes_frequency=REFERENCE_NES_FREQUENCY,
            expected=Fraction(31),
        ),
        TestCase(
            tempo=75,
            speed=6,
            nes_frequency=60,
            expected=Fraction(12),
        ),
        TestCase(
            tempo=210,
            speed=6,
            nes_frequency=60,
            expected=Fraction(30, 7),
        ),
        TestCase(
            tempo=150,
            speed=6,
            nes_frequency=50,
            expected=Fraction(5),
        ),
        TestCase(
            tempo=150,
            speed=6,
            nes_frequency=30,
            expected=Fraction(3),
        ),
        TestCase(
            tempo=32,
            speed=1,
            nes_frequency=60,
            expected=Fraction(75, 16),
        ),
        TestCase(
            tempo=255,
            speed=31,
            nes_frequency=300,
            expected=Fraction(1550, 17),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_ticks_per_row(self, test_case: TestCase) -> None:
        rate = RowRate.from_parameters(
            tempo=test_case.tempo,
            speed=test_case.speed,
            nes_frequency=test_case.nes_frequency,
        )
        assert rate.ticks_per_row == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_ticks_per_row_follows_the_reference_formula(self, test_case: TestCase) -> None:
        rate = RowRate.from_parameters(
            tempo=test_case.tempo,
            speed=test_case.speed,
            nes_frequency=test_case.nes_frequency,
        )
        assert rate.ticks_per_row == Fraction(
            test_case.speed * test_case.nes_frequency * REFERENCE_TEMPO,
            test_case.tempo * REFERENCE_NES_FREQUENCY,
        )

    def test_speed_states_the_tick_count_at_the_reference(self) -> None:
        for speed in range(1, 32):
            rate = RowRate.from_parameters(
                tempo=REFERENCE_TEMPO,
                speed=speed,
                nes_frequency=REFERENCE_NES_FREQUENCY,
            )
            assert rate.ticks_per_row == speed

    def test_settings_and_parameters_agree(self) -> None:
        settings = ProjectSettings(tempo=210, speed=6, nes_frequency=60)
        assert RowRate.from_settings(settings) == RowRate.from_parameters(
            tempo=settings.tempo,
            speed=settings.speed,
            nes_frequency=settings.nes_frequency,
        )
