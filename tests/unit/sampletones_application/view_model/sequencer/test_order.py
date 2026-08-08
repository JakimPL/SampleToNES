from dataclasses import dataclass
from typing import Dict, List, Optional

import pytest

from sampletones_application.view_model.sequencer.order import (
    OrderEntryViewModel,
    SequencerOrderTrackerViewModel,
    SequencerOrderViewModel,
)
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import display_id
from sampletones_shared.constants.symbols import MIXED
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

_EMPTY = display_id(None)


def _tracker(
    channels: Dict[GeneratorName, List[Optional[int]]],
) -> SequencerOrderTrackerViewModel:
    views = {
        generator: SequencerOrderViewModel(
            generator=generator,
            entries=tuple(
                OrderEntryViewModel(
                    position=position,
                    pattern_index=index,
                )
                for position, index in enumerate(indices)
            ),
        )
        for generator, indices in channels.items()
    }
    position_count = max(
        (len(view.entries) for view in views.values()),
        default=0,
    )
    return SequencerOrderTrackerViewModel(
        position_count=position_count,
        channels=views,
    )


def _uniform(*indices: Optional[int]) -> Dict[GeneratorName, List[Optional[int]]]:
    return {generator: list(indices) for generator in GeneratorName.items()}


def test_entry_label_renders_index_and_empty_slot() -> None:
    tracker = _tracker(_uniform(5, None))

    assert tracker.entry_label(GeneratorName.PULSE1, 0) == display_id(5)
    assert tracker.entry_label(GeneratorName.PULSE1, 1) == _EMPTY


class TestMasterLabel(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class MasterCase(BaseRegularTestCase):
        label: str
        channels: Dict[GeneratorName, List[Optional[int]]]
        expected: str

    test_cases = (
        MasterCase(
            label="shared_index",
            channels=_uniform(5),
            expected=display_id(5),
        ),
        MasterCase(
            label="all_empty",
            channels=_uniform(None),
            expected=_EMPTY,
        ),
        MasterCase(
            label="divergent_index",
            channels={
                GeneratorName.PULSE1: [5],
                GeneratorName.PULSE2: [5],
                GeneratorName.TRIANGLE: [7],
                GeneratorName.NOISE: [5],
            },
            expected=MIXED,
        ),
        MasterCase(
            label="index_versus_empty",
            channels={
                GeneratorName.PULSE1: [5],
                GeneratorName.PULSE2: [5],
                GeneratorName.TRIANGLE: [None],
                GeneratorName.NOISE: [5],
            },
            expected=MIXED,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_master_label_aggregates_across_channels(
        self,
        case: MasterCase,
    ) -> None:
        tracker = _tracker(case.channels)

        assert tracker.master_label(0) == case.expected
