from dataclasses import dataclass
from typing import Dict, FrozenSet

import pytest

from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
)
from sampletones_core.constants.enums import GeneratorName
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
) -> SequencerCellViewModel:
    return SequencerCellViewModel(
        instrument=instrument,
        transpose=transpose,
        volume=volume,
    )


def _empty_cell() -> SequencerCellViewModel:
    return _cell()


_OCCUPIED = _cell(
    instrument=display_id(0),
    transpose=display_transpose(5),
    volume=display_volume(8),
)


def _row_cells(
    **overrides: SequencerCellViewModel,
) -> Dict[GeneratorName, SequencerCellViewModel]:
    cells = {generator: _empty_cell() for generator in GeneratorName.items()}
    for name, cell in overrides.items():
        cells[GeneratorName[name.upper()]] = cell

    return cells


class TestSampleColumnAggregate(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class AggregateCase(BaseRegularTestCase):
        cells: Dict[GeneratorName, SequencerCellViewModel]
        relevant_generators: FrozenSet[GeneratorName]
        expected_instrument: str
        expected_transpose: str
        expected_volume: str

    test_cases = (
        AggregateCase(
            label="no_relevant_channels_fall_back_to_defaults",
            cells=_row_cells(),
            relevant_generators=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="transpose_and_volume_span_all_channels_when_no_sample_is_present",
            cells={generator: _cell(volume=display_volume(8)) for generator in GeneratorName.items()},
            relevant_generators=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="single_relevant_channel_present",
            cells=_row_cells(pulse1=_OCCUPIED),
            relevant_generators=frozenset({GeneratorName.PULSE1}),
            expected_instrument=display_id(0),
            expected_transpose=display_transpose(5),
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="sample_present_across_all_its_relevant_channels",
            cells=_row_cells(pulse1=_OCCUPIED, triangle=_OCCUPIED),
            relevant_generators=frozenset(
                {
                    GeneratorName.PULSE1,
                    GeneratorName.TRIANGLE,
                }
            ),
            expected_instrument=display_id(0),
            expected_transpose=display_transpose(5),
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="sample_missing_from_one_relevant_channel_is_mixed",
            cells=_row_cells(pulse1=_OCCUPIED),
            relevant_generators=frozenset(
                {
                    GeneratorName.PULSE1,
                    GeneratorName.TRIANGLE,
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
            relevant_generators=frozenset(
                {
                    GeneratorName.PULSE1,
                    GeneratorName.TRIANGLE,
                }
            ),
            expected_instrument=display_id(0),
            expected_transpose=MIXED,
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="all_channels_note_off_reads_as_note_off",
            cells={generator: _cell(instrument=NOTE_OFF) for generator in GeneratorName.items()},
            relevant_generators=frozenset(),
            expected_instrument=NOTE_OFF,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="half_cut_row_is_mixed",
            cells=_row_cells(pulse1=_cell(instrument=NOTE_OFF)),
            relevant_generators=frozenset(),
            expected_instrument=MIXED,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="zero_transpose_beside_an_empty_one_is_mixed",
            cells=_row_cells(pulse1=_cell(transpose=display_transpose(0))),
            relevant_generators=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=MIXED,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="zero_transpose_shared_by_every_channel_reads_as_zero",
            cells={generator: _cell(transpose=display_transpose(0)) for generator in GeneratorName.items()},
            relevant_generators=frozenset(),
            expected_instrument=_EMPTY_INSTRUMENT,
            expected_transpose=display_transpose(0),
            expected_volume=_EMPTY_VOLUME,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_sample_column_aggregates_over_relevant_channels(
        self,
        case: AggregateCase,
    ) -> None:
        row = SequencerRowViewModel(
            index=0,
            cells=case.cells,
            relevant_generators=case.relevant_generators,
        )

        assert row.sample_instrument == case.expected_instrument
        assert row.sample_transpose == case.expected_transpose
        assert row.sample_volume == case.expected_volume
