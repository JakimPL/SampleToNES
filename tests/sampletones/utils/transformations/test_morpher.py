from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest
from pydantic import ValidationError

from sampletones.utils.transformations.functions import identity
from sampletones.utils.transformations.morpher import PowerMorpher
from sampletones.utils.transformations.transformation import Transformation
from tests.sampletones.errors import expect_error


class TestPowerMorpherValidGamma:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        gamma: float
        expected_power: float
        should_be_identity: bool
        test_id: str

    test_cases = [
        TestCase(
            gamma=0.0,
            expected_power=0.25,
            should_be_identity=False,
            test_id="gamma_0_flat",
        ),
        TestCase(
            gamma=0.25,
            expected_power=0.5,
            should_be_identity=False,
            test_id="gamma_0_25",
        ),
        TestCase(
            gamma=0.5,
            expected_power=1.0,
            should_be_identity=True,
            test_id="gamma_0_5_identity",
        ),
        TestCase(
            gamma=0.75,
            expected_power=2.0,
            should_be_identity=False,
            test_id="gamma_0_75",
        ),
        TestCase(
            gamma=1.0,
            expected_power=4.0,
            should_be_identity=False,
            test_id="gamma_1_sharp",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_morpher(self, test_case: TestCase) -> None:
        morpher = PowerMorpher(gamma=test_case.gamma)
        assert morpher.gamma == test_case.gamma
        assert morpher.power == test_case.expected_power
        assert isinstance(morpher.transformation, Transformation)
        if test_case.should_be_identity:
            assert morpher.transformation.forward is identity
            assert morpher.transformation.backward is identity
        else:
            assert morpher.transformation.forward is not identity
            assert morpher.transformation.backward is not identity


class TestPowerMorpherInvalidGamma:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        gamma: float
        test_id: str

    test_cases = [
        TestCase(
            gamma=np.nan,
            test_id="gamma_nan",
        ),
        TestCase(
            gamma=np.inf,
            test_id="gamma_inf",
        ),
        TestCase(
            gamma=-0.1,
            test_id="gamma_negative",
        ),
        TestCase(
            gamma=-1.0,
            test_id="gamma_minus_one",
        ),
        TestCase(
            gamma=1.1,
            test_id="gamma_above_one",
        ),
        TestCase(
            gamma=2.0,
            test_id="gamma_two",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda tc: tc.test_id,
    )
    def test_invalid_gamma(self, test_case: TestCase) -> None:
        if expect_error(PowerMorpher, ValidationError, gamma=test_case.gamma):
            return


class TestPowerMorpherEdgeCases:
    def test_cached_property_power(self) -> None:
        morpher = PowerMorpher(gamma=0.75)
        power1 = morpher.power
        power2 = morpher.power
        assert power1 is power2

    def test_cached_property_transformation(self) -> None:
        morpher = PowerMorpher(gamma=0.75)
        transformation1 = morpher.transformation
        transformation2 = morpher.transformation
        assert transformation1 is transformation2

    def test_frozen_model(self) -> None:
        morpher = PowerMorpher(gamma=0.5)
        if expect_error(lambda: setattr(morpher, "gamma", 0.75), ValidationError):
            return
