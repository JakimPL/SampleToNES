from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions.reconstructor.state import ReconstructionState
from tests.suite.case import BaseTestCase


def _make_instruction() -> PulseInstruction:
    return PulseInstruction(on=True, pitch=60, volume=10, duty_cycle=0)


@dataclass(frozen=True, kw_only=True)
class NamesCase(BaseTestCase):
    label: str
    names: List[ChannelName]


NAMES_CASES = [
    NamesCase(label="single", names=[ChannelName.PULSE1]),
    NamesCase(
        label="multiple",
        names=[
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
            ChannelName.NOISE,
        ],
    ),
]


class TestReconstructionStateCreate:
    def test_empty_list_creates_empty_instruction_dicts(self) -> None:
        state = ReconstructionState.create([])
        assert state.instructions == {}

    @pytest.mark.parametrize("case", NAMES_CASES, ids=lambda c: c.label)
    def test_generator_names_stored(self, case: NamesCase) -> None:
        state = ReconstructionState.create(case.names)
        assert state.channel_names == case.names

    @pytest.mark.parametrize("case", NAMES_CASES, ids=lambda c: c.label)
    def test_each_generator_initializes_to_empty_list(self, case: NamesCase) -> None:
        state = ReconstructionState.create(case.names)
        for name in case.names:
            assert state.instructions[name] == []


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
        return ReconstructionState.create([ChannelName.PULSE1, ChannelName.TRIANGLE])

    def test_instruction_added_for_correct_generator(self, state: ReconstructionState) -> None:
        instruction = _make_instruction()
        state.append(ChannelName.PULSE1, instruction)
        assert state.instructions[ChannelName.PULSE1] == [instruction]

    @pytest.mark.parametrize("case", ACCUMULATE_CASES, ids=lambda c: c.label)
    def test_multiple_appends_accumulate_in_order(self, case: TestCase, state: ReconstructionState) -> None:
        for _ in range(case.count):
            state.append(ChannelName.PULSE1, _make_instruction())
        assert len(state.instructions[ChannelName.PULSE1]) == case.count

    def test_append_to_separate_generators_are_independent(self, state: ReconstructionState) -> None:
        state.append(ChannelName.PULSE1, _make_instruction())
        state.append(ChannelName.TRIANGLE, _make_instruction())
        assert len(state.instructions[ChannelName.PULSE1]) == 1
        assert len(state.instructions[ChannelName.TRIANGLE]) == 1


class TestReconstructionStateDrop:
    @pytest.fixture
    def state(self) -> ReconstructionState:
        state = ReconstructionState.create([ChannelName.PULSE1, ChannelName.TRIANGLE])
        state.append(ChannelName.PULSE1, _make_instruction())
        return state

    def test_dropping_a_channel_releases_its_stream(self, state: ReconstructionState) -> None:
        state.drop(ChannelName.TRIANGLE)

        assert state.channel_names == [ChannelName.PULSE1]
        assert set(state.instructions) == {ChannelName.PULSE1}

    def test_the_remaining_channels_keep_their_frames(self, state: ReconstructionState) -> None:
        state.drop(ChannelName.TRIANGLE)

        assert len(state.instructions[ChannelName.PULSE1]) == 1
