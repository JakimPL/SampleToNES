from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional

import pytest

from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import (
    NOTE_OFF,
    display_id,
    display_transpose,
    display_volume,
)
from sampletones_shared.constants.symbols import MIXED
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

_EMPTY_INSTRUMENT = display_id(None)
_EMPTY_TRANSPOSE = display_transpose(None)
_EMPTY_VOLUME = display_volume(None)


def _cell(
    *,
    instrument: str = _EMPTY_INSTRUMENT,
    transpose: str = _EMPTY_TRANSPOSE,
    volume: str = _EMPTY_VOLUME,
    kind: Optional[VoiceKind] = None,
) -> SequencerCellViewModel:
    return SequencerCellViewModel(
        instrument=instrument,
        transpose=transpose,
        volume=volume,
        kind=kind,
    )


def _empty_cell() -> SequencerCellViewModel:
    return _cell()


_OCCUPIED = _cell(
    instrument=display_id(0),
    transpose=display_transpose(5),
    volume=display_volume(8),
    kind=VoiceKind.SAMPLE,
)


def _row_cells(
    **overrides: SequencerCellViewModel,
) -> Dict[ChannelName, SequencerCellViewModel]:
    cells = {channel: _empty_cell() for channel in ChannelName.items()}
    for name, cell in overrides.items():
        cells[ChannelName[name.upper()]] = cell

    return cells


class TestSampleColumnAggregate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class AggregateCase(BaseRegularTestCase):
        cells: Dict[ChannelName, SequencerCellViewModel]
        sample_channels: FrozenSet[ChannelName]
        expected_instrument: str
        expected_transpose: str
        expected_volume: str

    test_cases = (
        AggregateCase(
            label="no_sample_channels_fall_back_to_defaults",
            cells=_row_cells(),
            sample_channels=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="transpose_and_volume_span_all_channels_when_no_sample_is_present",
            cells={channel: _cell(volume=display_volume(8)) for channel in ChannelName.items()},
            sample_channels=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="a_single_sample_channel_present",
            cells=_row_cells(pulse1=_OCCUPIED),
            sample_channels=frozenset({ChannelName.PULSE1}),
            expected_instrument=display_id(0),
            expected_transpose=display_transpose(5),
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="a_sample_present_across_every_channel_it_covers",
            cells=_row_cells(pulse1=_OCCUPIED, triangle=_OCCUPIED),
            sample_channels=frozenset(
                {
                    ChannelName.PULSE1,
                    ChannelName.TRIANGLE,
                }
            ),
            expected_instrument=display_id(0),
            expected_transpose=display_transpose(5),
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="a_sample_missing_from_one_of_its_channels_is_mixed",
            cells=_row_cells(pulse1=_OCCUPIED),
            sample_channels=frozenset(
                {
                    ChannelName.PULSE1,
                    ChannelName.TRIANGLE,
                }
            ),
            expected_instrument=MIXED,
            expected_transpose=MIXED,
            expected_volume=MIXED,
        ),
        AggregateCase(
            label="diverging_transpose_is_mixed_while_instrument_is_uniform",
            cells=_row_cells(
                pulse1=_OCCUPIED,
                triangle=_cell(
                    instrument=display_id(0),
                    transpose=_EMPTY_TRANSPOSE,
                    volume=display_volume(8),
                ),
            ),
            sample_channels=frozenset(
                {
                    ChannelName.PULSE1,
                    ChannelName.TRIANGLE,
                }
            ),
            expected_instrument=display_id(0),
            expected_transpose=MIXED,
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="an_instrument_alone_on_a_row_leaves_the_sample_column_empty",
            cells=_row_cells(
                pulse1=_cell(
                    instrument=display_id(3),
                    kind=VoiceKind.INSTRUMENT,
                ),
            ),
            sample_channels=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="an_instrument_beside_a_sample_leaves_the_samples_reading_alone",
            cells=_row_cells(
                pulse1=_OCCUPIED,
                triangle=_OCCUPIED,
                noise=_cell(
                    instrument=display_id(3),
                    kind=VoiceKind.INSTRUMENT,
                ),
            ),
            sample_channels=frozenset(
                {
                    ChannelName.PULSE1,
                    ChannelName.TRIANGLE,
                }
            ),
            expected_instrument=display_id(0),
            expected_transpose=display_transpose(5),
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="all_channels_note_off_reads_as_note_off",
            cells={channel: _cell(instrument=NOTE_OFF) for channel in ChannelName.items()},
            sample_channels=frozenset(),
            expected_instrument=NOTE_OFF,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="half_cut_row_is_mixed",
            cells=_row_cells(pulse1=_cell(instrument=NOTE_OFF)),
            sample_channels=frozenset(),
            expected_instrument=MIXED,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="zero_transpose_beside_an_empty_one_is_mixed",
            cells=_row_cells(pulse1=_cell(transpose=display_transpose(0))),
            sample_channels=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=MIXED,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="zero_transpose_shared_by_every_channel_reads_as_zero",
            cells={channel: _cell(transpose=display_transpose(0)) for channel in ChannelName.items()},
            sample_channels=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=display_transpose(0),
            expected_volume=_EMPTY_VOLUME,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_sample_column_aggregates_over_the_channels_it_spans(
        self,
        case: AggregateCase,
    ) -> None:
        row = SequencerRowViewModel(
            index=0,
            cells=case.cells,
            sample_channels=case.sample_channels,
        )

        assert row.sample == case.expected_instrument
        assert row.transpose == case.expected_transpose
        assert row.volume == case.expected_volume
