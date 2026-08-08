from dataclasses import dataclass
from typing import FrozenSet

import pytest

from sampletones_application.view_model.sequencer.channels import (
    SequencerChannelsViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from tests.suite.case import BaseRegularTestCase

ALL_CHANNELS = frozenset(GeneratorName.items())

PULSE1 = GeneratorName.PULSE1
PULSE2 = GeneratorName.PULSE2
TRIANGLE = GeneratorName.TRIANGLE
NOISE = GeneratorName.NOISE


@dataclass(frozen=True, kw_only=True)
class AllMutedCase(BaseRegularTestCase):
    muted: FrozenSet[GeneratorName]
    expected: bool


ALL_MUTED_CASES = [
    AllMutedCase(label="nothing silenced", muted=frozenset(), expected=False),
    AllMutedCase(label="one silenced", muted=frozenset({PULSE1}), expected=False),
    AllMutedCase(label="three silenced", muted=frozenset({PULSE1, PULSE2, NOISE}), expected=False),
    AllMutedCase(label="every channel silenced", muted=ALL_CHANNELS, expected=True),
]

ANY_MUTED_CASES = [
    AllMutedCase(label="nothing silenced", muted=frozenset(), expected=False),
    AllMutedCase(label="one silenced", muted=frozenset({PULSE1}), expected=True),
    AllMutedCase(label="three silenced", muted=frozenset({PULSE1, PULSE2, NOISE}), expected=True),
    AllMutedCase(label="every channel silenced", muted=ALL_CHANNELS, expected=True),
]


class TestAllMuted:
    @pytest.mark.parametrize("case", ALL_MUTED_CASES, ids=lambda case: case.label)
    def test_all_muted_reports_full_silence(self, case: AllMutedCase) -> None:
        view_model = SequencerChannelsViewModel(muted=case.muted)

        assert view_model.all_muted is case.expected


class TestAnyMuted:
    @pytest.mark.parametrize("case", ANY_MUTED_CASES, ids=lambda case: case.label)
    def test_any_muted_reports_a_silenced_channel(self, case: AllMutedCase) -> None:
        view_model = SequencerChannelsViewModel(muted=case.muted)

        assert view_model.any_muted is case.expected

    def test_the_two_readings_agree_in_full_silence(self) -> None:
        view_model = SequencerChannelsViewModel(muted=ALL_CHANNELS)

        assert view_model.any_muted and view_model.all_muted


class TestIsSoloed:
    @pytest.mark.parametrize("generator", GeneratorName.items(), ids=lambda generator: generator.value)
    def test_the_one_audible_channel_reads_as_soloed(self, generator: GeneratorName) -> None:
        view_model = SequencerChannelsViewModel(muted=ALL_CHANNELS - {generator})

        soloed = {other for other in GeneratorName.items() if view_model.is_soloed(other)}

        assert soloed == {generator}

    def test_no_channel_is_soloed_in_a_full_mix(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset())

        assert not any(view_model.is_soloed(generator) for generator in GeneratorName.items())

    def test_no_channel_is_soloed_in_full_silence(self) -> None:
        view_model = SequencerChannelsViewModel(muted=ALL_CHANNELS)

        assert not any(view_model.is_soloed(generator) for generator in GeneratorName.items())

    def test_two_audible_channels_leave_neither_soloed(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset({PULSE1, PULSE2}))

        assert not view_model.is_soloed(TRIANGLE)
        assert not view_model.is_soloed(NOISE)


class TestIsMuted:
    @pytest.mark.parametrize("generator", GeneratorName.items(), ids=lambda generator: generator.value)
    def test_is_muted_reports_membership_of_the_mute_set(self, generator: GeneratorName) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset({TRIANGLE, NOISE}))

        assert view_model.is_muted(generator) is (generator in {TRIANGLE, NOISE})

    def test_no_channel_is_muted_in_a_full_mix(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset())

        assert not any(view_model.is_muted(generator) for generator in GeneratorName.items())
