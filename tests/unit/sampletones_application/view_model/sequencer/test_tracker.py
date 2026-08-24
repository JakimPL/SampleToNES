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

_EMPTY_VOICE = display_id(None)
_EMPTY_TRANSPOSE = display_transpose(None)
_EMPTY_VOLUME = display_volume(None)


def _cell(
    *,
    voice: str = _EMPTY_VOICE,
    transpose: str = _EMPTY_TRANSPOSE,
    volume: str = _EMPTY_VOLUME,
    kind: Optional[VoiceKind] = None,
) -> SequencerCellViewModel:
    return SequencerCellViewModel(
        voice=voice,
        transpose=transpose,
        volume=volume,
        kind=kind,
    )


def _empty_cell() -> SequencerCellViewModel:
    return _cell()


_OCCUPIED = _cell(
    voice=display_id(0),
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
        expected_sample: str
        expected_transpose: str
        expected_volume: str

    test_cases = (
        AggregateCase(
            label="no_sample_channels_fall_back_to_defaults",
            cells=_row_cells(),
            sample_channels=frozenset(),
            expected_sample=_EMPTY_VOICE,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="transpose_and_volume_span_all_channels_when_no_sample_is_present",
            cells={channel: _cell(volume=display_volume(8)) for channel in ChannelName.items()},
            sample_channels=frozenset(),
            expected_sample=_EMPTY_VOICE,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="a_single_sample_channel_present",
            cells=_row_cells(pulse1=_OCCUPIED),
            sample_channels=frozenset({ChannelName.PULSE1}),
            expected_sample=display_id(0),
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
            expected_sample=display_id(0),
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
            expected_sample=MIXED,
            expected_transpose=MIXED,
            expected_volume=MIXED,
        ),
        AggregateCase(
            label="diverging_transpose_is_mixed_while_the_sample_is_uniform",
            cells=_row_cells(
                pulse1=_OCCUPIED,
                triangle=_cell(
                    voice=display_id(0),
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
            expected_sample=display_id(0),
            expected_transpose=MIXED,
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="an_instrument_alone_on_a_row_leaves_the_sample_column_empty",
            cells=_row_cells(
                pulse1=_cell(
                    voice=display_id(3),
                    kind=VoiceKind.INSTRUMENT,
                ),
            ),
            sample_channels=frozenset(),
            expected_sample=_EMPTY_VOICE,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="an_instrument_beside_a_sample_leaves_the_samples_reading_alone",
            cells=_row_cells(
                pulse1=_OCCUPIED,
                triangle=_OCCUPIED,
                noise=_cell(
                    voice=display_id(3),
                    kind=VoiceKind.INSTRUMENT,
                ),
            ),
            sample_channels=frozenset(
                {
                    ChannelName.PULSE1,
                    ChannelName.TRIANGLE,
                }
            ),
            expected_sample=display_id(0),
            expected_transpose=display_transpose(5),
            expected_volume=display_volume(8),
        ),
        AggregateCase(
            label="all_channels_note_off_reads_as_note_off",
            cells={channel: _cell(voice=NOTE_OFF) for channel in ChannelName.items()},
            sample_channels=frozenset(),
            expected_sample=NOTE_OFF,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="half_cut_row_is_mixed",
            cells=_row_cells(pulse1=_cell(voice=NOTE_OFF)),
            sample_channels=frozenset(),
            expected_sample=MIXED,
            expected_transpose=_EMPTY_TRANSPOSE,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="zero_transpose_beside_an_empty_one_is_mixed",
            cells=_row_cells(pulse1=_cell(transpose=display_transpose(0))),
            sample_channels=frozenset(),
            expected_sample=_EMPTY_VOICE,
            expected_transpose=MIXED,
            expected_volume=_EMPTY_VOLUME,
        ),
        AggregateCase(
            label="zero_transpose_shared_by_every_channel_reads_as_zero",
            cells={channel: _cell(transpose=display_transpose(0)) for channel in ChannelName.items()},
            sample_channels=frozenset(),
            expected_sample=_EMPTY_VOICE,
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

        assert row.sample == case.expected_sample
        assert row.transpose == case.expected_transpose
        assert row.volume == case.expected_volume


class TestWhichKindTheSampleColumnNames:
    """The slot's kind is what colors it, so it states one only where its channels agree."""

    @staticmethod
    def _row(
        cells: Dict[ChannelName, SequencerCellViewModel],
        sample_channels: FrozenSet[ChannelName],
    ) -> SequencerRowViewModel:
        return SequencerRowViewModel(
            index=0,
            cells=cells,
            sample_channels=sample_channels,
        )

    def test_a_row_naming_nothing_states_no_kind(self) -> None:
        row = self._row(_row_cells(), frozenset())

        assert row.sample_kind is None

    def test_a_sample_across_its_channels_states_the_sample_kind(self) -> None:
        row = self._row(
            _row_cells(pulse1=_OCCUPIED, triangle=_OCCUPIED),
            frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE}),
        )

        assert row.sample_kind is VoiceKind.SAMPLE

    def test_a_sample_missing_from_one_of_its_channels_states_no_kind(self) -> None:
        """The reading is mixed there, and a mixed cell speaks for no one voice."""
        row = self._row(
            _row_cells(pulse1=_OCCUPIED),
            frozenset({ChannelName.PULSE1, ChannelName.TRIANGLE}),
        )

        assert row.sample_kind is None

    def test_an_instrument_alone_on_a_row_states_no_kind(self) -> None:
        """It is placed in its own channel column, so the sample column speaks for none of it."""
        row = self._row(
            _row_cells(pulse1=_cell(voice=display_id(3), kind=VoiceKind.INSTRUMENT)),
            frozenset(),
        )

        assert row.sample_kind is None

    def test_an_instrument_beside_a_sample_leaves_the_sample_kind_standing(self) -> None:
        row = self._row(
            _row_cells(
                pulse1=_OCCUPIED,
                noise=_cell(voice=display_id(3), kind=VoiceKind.INSTRUMENT),
            ),
            frozenset({ChannelName.PULSE1}),
        )

        assert row.sample_kind is VoiceKind.SAMPLE

    def test_a_cut_row_states_no_kind(self) -> None:
        """A cut names no voice, so the slot reads it in the shade an empty one takes."""
        row = self._row(
            {channel: _cell(voice=NOTE_OFF) for channel in ChannelName.items()},
            frozenset(),
        )

        assert row.sample_kind is None
