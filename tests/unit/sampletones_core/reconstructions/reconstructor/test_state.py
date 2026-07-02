from __future__ import annotations

from dataclasses import dataclass
from typing import List
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.approximation import ApproximationData
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from tests.suite.case import BaseTestCase

_FRAME_LENGTH = 16


def _make_approximation_data(generator_name: GeneratorName) -> ApproximationData:
    return ApproximationData(
        generator_name=generator_name,
        approximation=MagicMock(spec=Fragment),
        instruction=PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0),
    )


def _make_audio(value: float = 1.0) -> np.ndarray:
    return np.full(_FRAME_LENGTH, value, dtype=np.float32)


@dataclass(frozen=True, kw_only=True)
class NamesCase(BaseTestCase):
    label: str
    names: List[GeneratorName]


NAMES_CASES = [
    NamesCase(label="single", names=[GeneratorName.PULSE1]),
    NamesCase(
        label="multiple",
        names=[
            GeneratorName.PULSE1,
            GeneratorName.TRIANGLE,
            GeneratorName.NOISE,
        ],
    ),
]


class TestReconstructionStateCreate:
    def test_empty_list_creates_empty_instruction_dicts(self) -> None:
        state = ReconstructionState.create([])
        assert state.instructions == {}

    def test_empty_list_creates_empty_approximation_dicts(self) -> None:
        state = ReconstructionState.create([])
        assert state.approximations == {}

    @pytest.mark.parametrize("case", NAMES_CASES, ids=lambda c: c.label)
    def test_generator_names_stored(self, case: NamesCase) -> None:
        state = ReconstructionState.create(case.names)
        assert state.generator_names == case.names

    @pytest.mark.parametrize("case", NAMES_CASES, ids=lambda c: c.label)
    def test_each_generator_initializes_to_empty_list(self, case: NamesCase) -> None:
        state = ReconstructionState.create(case.names)
        for name in case.names:
            assert state.instructions[name] == []
            assert state.approximations[name] == []


class TestReconstructionStateAppend:
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseTestCase):
        label: str
        count: int

    ACCUMULATE_CASES = [
        TestCase(label="one", count=1),
        TestCase(label="two", count=2),
        TestCase(label="three", count=3),
    ]

    @pytest.fixture
    def state(self) -> ReconstructionState:
        return ReconstructionState.create([GeneratorName.PULSE1, GeneratorName.TRIANGLE])

    def test_instruction_added_for_correct_generator(self, state: ReconstructionState) -> None:
        approximation_data = _make_approximation_data(GeneratorName.PULSE1)
        state.append(approximation_data, _make_audio())
        assert state.instructions[GeneratorName.PULSE1] == [approximation_data.instruction]

    def test_approximation_added_for_correct_generator(self, state: ReconstructionState) -> None:
        audio = _make_audio(0.5)
        state.append(_make_approximation_data(GeneratorName.PULSE1), audio)
        assert len(state.approximations[GeneratorName.PULSE1]) == 1
        np.testing.assert_array_equal(state.approximations[GeneratorName.PULSE1][0], audio)

    @pytest.mark.parametrize("case", ACCUMULATE_CASES, ids=lambda c: c.label)
    def test_multiple_appends_accumulate_in_order(self, case: TestCase, state: ReconstructionState) -> None:
        for i in range(case.count):
            state.append(_make_approximation_data(GeneratorName.PULSE1), _make_audio(float(i)))
        assert len(state.instructions[GeneratorName.PULSE1]) == case.count
        assert len(state.approximations[GeneratorName.PULSE1]) == case.count

    def test_append_to_separate_generators_are_independent(self, state: ReconstructionState) -> None:
        state.append(_make_approximation_data(GeneratorName.PULSE1), _make_audio(1.0))
        state.append(_make_approximation_data(GeneratorName.TRIANGLE), _make_audio(2.0))
        assert len(state.instructions[GeneratorName.PULSE1]) == 1
        assert len(state.approximations[GeneratorName.PULSE1]) == 1
        assert len(state.instructions[GeneratorName.TRIANGLE]) == 1
        assert len(state.approximations[GeneratorName.TRIANGLE]) == 1
