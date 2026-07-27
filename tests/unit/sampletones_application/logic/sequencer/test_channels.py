from dataclasses import dataclass
from typing import Callable, FrozenSet, List, Tuple

import pytest

from sampletones_application.logic.sequencer.channels import (
    ALL_CHANNELS,
    SequencerChannelsLogic,
)
from sampletones_application.view_model.sequencer.channels import SequencerChannelsViewModel
from sampletones_core.constants.enums import GeneratorName
from tests.suite.case import BaseTestCase

Gesture = Callable[[SequencerChannelsLogic], None]

PULSE1 = GeneratorName.PULSE1
PULSE2 = GeneratorName.PULSE2
TRIANGLE = GeneratorName.TRIANGLE
NOISE = GeneratorName.NOISE


def toggle(generator: GeneratorName) -> Gesture:
    return lambda logic: logic.toggle(generator)


def solo(generator: GeneratorName) -> Gesture:
    return lambda logic: logic.solo(generator)


def toggle_all() -> Gesture:
    return lambda logic: logic.toggle_all()


def unmute_all() -> Gesture:
    return lambda logic: logic.unmute_all()


def reset() -> Gesture:
    return lambda logic: logic.reset()


@dataclass(frozen=True, kw_only=True)
class GestureCase(BaseTestCase):
    label: str
    gestures: Tuple[Gesture, ...]
    expected_muted: FrozenSet[GeneratorName]


GESTURE_CASES = [
    GestureCase(
        label="toggle silences one channel",
        gestures=(toggle(PULSE1),),
        expected_muted=frozenset({PULSE1}),
    ),
    GestureCase(
        label="toggling twice returns it to audible",
        gestures=(toggle(PULSE1), toggle(PULSE1)),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="toggles accumulate across channels",
        gestures=(toggle(PULSE1), toggle(NOISE)),
        expected_muted=frozenset({PULSE1, NOISE}),
    ),
    GestureCase(
        label="solo silences the other three",
        gestures=(solo(TRIANGLE),),
        expected_muted=ALL_CHANNELS - {TRIANGLE},
    ),
    GestureCase(
        label="soloing again returns to the mix the solo interrupted",
        gestures=(toggle(PULSE1), solo(TRIANGLE), solo(TRIANGLE)),
        expected_muted=frozenset({PULSE1}),
    ),
    GestureCase(
        label="soloing twice from a full mix leaves everything audible",
        gestures=(solo(TRIANGLE), solo(TRIANGLE)),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="soloing another channel moves the solo",
        gestures=(solo(TRIANGLE), solo(NOISE)),
        expected_muted=ALL_CHANNELS - {NOISE},
    ),
    GestureCase(
        label="leaving a moved solo returns to the previous solo",
        gestures=(solo(TRIANGLE), solo(NOISE), solo(NOISE)),
        expected_muted=ALL_CHANNELS - {TRIANGLE},
    ),
    GestureCase(
        label="a toggle after a solo becomes what the next solo returns to",
        gestures=(solo(TRIANGLE), toggle(PULSE1), solo(TRIANGLE), solo(TRIANGLE)),
        expected_muted=frozenset({PULSE2, NOISE}),
    ),
    GestureCase(
        label="the master gesture silences everything from a full mix",
        gestures=(toggle_all(),),
        expected_muted=ALL_CHANNELS,
    ),
    GestureCase(
        label="the master gesture silences everything from a mixed set",
        gestures=(toggle(PULSE1), toggle_all()),
        expected_muted=ALL_CHANNELS,
    ),
    GestureCase(
        label="the master gesture silences the channel a solo left audible",
        gestures=(solo(TRIANGLE), toggle_all()),
        expected_muted=ALL_CHANNELS,
    ),
    GestureCase(
        label="the master gesture restores everything from full silence",
        gestures=(toggle_all(), toggle_all()),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="the master gesture becomes what the next solo returns to",
        gestures=(toggle(PULSE1), solo(TRIANGLE), toggle_all(), toggle_all(), solo(TRIANGLE), solo(TRIANGLE)),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="unmuting all clears a mixed set",
        gestures=(toggle(PULSE1), toggle(NOISE), unmute_all()),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="unmuting all clears a solo",
        gestures=(solo(TRIANGLE), unmute_all()),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="reset clears a mixed set",
        gestures=(toggle(PULSE1), solo(TRIANGLE), reset()),
        expected_muted=frozenset(),
    ),
    GestureCase(
        label="reset starts the next solo from a full mix",
        gestures=(toggle(PULSE1), solo(TRIANGLE), reset(), solo(TRIANGLE), solo(TRIANGLE)),
        expected_muted=frozenset(),
    ),
]


def _make_logic() -> Tuple[SequencerChannelsLogic, List[SequencerChannelsViewModel]]:
    logic = SequencerChannelsLogic()
    views: List[SequencerChannelsViewModel] = []
    logic.on_channels_changed = views.append
    return logic, views


def _perform(logic: SequencerChannelsLogic, gestures: Tuple[Gesture, ...]) -> None:
    for gesture in gestures:
        gesture(logic)


class TestGestures:
    @pytest.mark.parametrize("case", GESTURE_CASES, ids=lambda case: case.label)
    def test_gestures_produce_expected_mute_set(self, case: GestureCase) -> None:
        logic, _ = _make_logic()

        _perform(logic, case.gestures)

        assert logic.build_channels().muted == case.expected_muted

    @pytest.mark.parametrize("case", GESTURE_CASES, ids=lambda case: case.label)
    def test_active_channels_complement_the_mute_set(self, case: GestureCase) -> None:
        logic, _ = _make_logic()

        _perform(logic, case.gestures)

        assert logic.active_channels == ALL_CHANNELS - case.expected_muted


class TestInitialState:
    def test_every_channel_starts_audible(self) -> None:
        logic, _ = _make_logic()

        assert logic.active_channels == ALL_CHANNELS
        assert logic.build_channels().muted == frozenset()


class TestViewPush:
    def test_each_gesture_pushes_one_view(self) -> None:
        logic, views = _make_logic()

        logic.toggle(PULSE1)
        logic.solo(TRIANGLE)
        logic.toggle_all()
        logic.unmute_all()
        logic.reset()

        assert len(views) == 5

    def test_pushed_view_reports_the_silenced_channels(self) -> None:
        logic, views = _make_logic()

        logic.solo(TRIANGLE)

        assert views[-1].muted == ALL_CHANNELS - {TRIANGLE}
        assert views[-1].is_muted(PULSE1)
        assert not views[-1].is_muted(TRIANGLE)

    def test_push_channels_republishes_the_current_set(self) -> None:
        logic, views = _make_logic()
        logic.toggle(NOISE)

        logic.push_channels()

        assert len(views) == 2
        assert views[-1] == views[-2]
