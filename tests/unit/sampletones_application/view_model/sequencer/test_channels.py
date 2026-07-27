from dataclasses import dataclass
from typing import FrozenSet

import pytest

from sampletones_application.view_model.sequencer.channels import SequencerChannelsViewModel
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


class TestAllMuted:
    @pytest.mark.parametrize("case", ALL_MUTED_CASES, ids=lambda case: case.label)
    def test_all_muted_reports_full_silence(self, case: AllMutedCase) -> None:
        view_model = SequencerChannelsViewModel(muted=case.muted)

        assert view_model.all_muted is case.expected


class TestIsMuted:
    @pytest.mark.parametrize("generator", GeneratorName.items(), ids=lambda generator: generator.value)
    def test_is_muted_reports_membership_of_the_mute_set(self, generator: GeneratorName) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset({TRIANGLE, NOISE}))

        assert view_model.is_muted(generator) is (generator in {TRIANGLE, NOISE})

    def test_no_channel_is_muted_in_a_full_mix(self) -> None:
        view_model = SequencerChannelsViewModel(muted=frozenset())

        assert not any(view_model.is_muted(generator) for generator in GeneratorName.items())
