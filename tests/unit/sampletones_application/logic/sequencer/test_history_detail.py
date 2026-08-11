from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.history_detail import (
    SequencerHistoryDetail,
)
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.shared.history import (
    HistoryDetailRole,
    HistoryDetailSegment,
    HistoryDetailWord,
    HistoryDetailWordSegment,
)
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from tests.suite.sequencer import sample_reconstruction

Pair = Tuple[str, HistoryDetailRole]


def _controller() -> ProjectController:
    return ProjectController(ProjectManager())


def _formatter(controller: ProjectController) -> SequencerHistoryDetail:
    tracker_logic = SequencerTrackerLogic(controller)
    samples_logic = SequencerSamplesLogic(
        controller,
        MagicMock(),
        MagicMock(),
        scheduling=MagicMock(),
    )
    return SequencerHistoryDetail(tracker_logic, samples_logic)


def _pairs(segments: Tuple[HistoryDetailSegment, ...]) -> List[Pair]:
    return [(segment.text, segment.role) for segment in segments]


class TestTrackerDetails:
    def test_edit_row_single_channel_places_sample(self) -> None:
        controller = _controller()
        controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="lead")
        target = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="bass")
        formatter = _formatter(controller)

        segments = formatter.edit_row(10, GeneratorName.PULSE1, target.id, None, None)

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("P", HistoryDetailRole.CHANNEL),
            ("0A", HistoryDetailRole.ROW),
            (">", HistoryDetailRole.SEPARATOR),
            ("01", HistoryDetailRole.SAMPLE),
        ]

    def test_edit_row_sample_column_lists_the_samples_channels(self) -> None:
        controller = _controller()
        sample = controller.add_sample(
            sample_reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE, GeneratorName.NOISE]),
            name="chord",
        )
        formatter = _formatter(controller)

        segments = formatter.edit_row(0, None, sample.id, None, None)

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("PTN", HistoryDetailRole.CHANNEL),
            ("00", HistoryDetailRole.ROW),
            (">", HistoryDetailRole.SEPARATOR),
            ("00", HistoryDetailRole.SAMPLE),
        ]

    def test_edit_row_transpose_shows_subcolumn_and_value(self) -> None:
        controller = _controller()
        formatter = _formatter(controller)

        segments = formatter.edit_row(0, GeneratorName.TRIANGLE, None, 5, None)

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("T", HistoryDetailRole.CHANNEL),
            ("00", HistoryDetailRole.ROW),
            ("t", HistoryDetailRole.TRANSPOSE),
            ("+05", HistoryDetailRole.TRANSPOSE),
        ]

    def test_note_off_sample_column_lists_every_channel(self) -> None:
        controller = _controller()
        formatter = _formatter(controller)

        segments = formatter.note_off(0, None)

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("PpTN", HistoryDetailRole.CHANNEL),
            ("00", HistoryDetailRole.ROW),
        ]

    def test_clear_subcolumn_names_the_column(self) -> None:
        controller = _controller()
        formatter = _formatter(controller)

        segments = formatter.clear_subcolumn(0, GeneratorName.NOISE, SubColumn.VOLUME)

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("N", HistoryDetailRole.CHANNEL),
            ("00", HistoryDetailRole.ROW),
            ("v", HistoryDetailRole.VOLUME),
        ]

    def test_a_block_reads_as_the_channels_and_the_rows_it_covers(self) -> None:
        formatter = _formatter(_controller())

        segments = formatter.tracker_block(
            TrackerRegion(
                first_row=4,
                last_row=11,
                first_slot=TrackerSlot(GeneratorName.PULSE1, SubColumn.TRANSPOSE).flat_index,
                last_slot=TrackerSlot(GeneratorName.PULSE2, SubColumn.INSTRUMENT).flat_index,
            )
        )

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("Pp", HistoryDetailRole.CHANNEL),
            ("04-0B", HistoryDetailRole.ROW),
        ]

    def test_a_block_reaching_the_sample_column_reads_as_every_channel(self) -> None:
        formatter = _formatter(_controller())

        segments = formatter.tracker_block(
            TrackerRegion(
                first_row=0,
                last_row=0,
                first_slot=TrackerSlot(None, SubColumn.INSTRUMENT).flat_index,
                last_slot=TrackerSlot(None, SubColumn.VOLUME).flat_index,
            )
        )

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("PpTN", HistoryDetailRole.CHANNEL),
            ("00", HistoryDetailRole.ROW),
        ]

    def test_a_paste_reads_as_the_cell_it_was_written_from(self) -> None:
        formatter = _formatter(_controller())

        segments = formatter.tracker_paste(TrackerCell(row=3, generator=GeneratorName.NOISE))

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("N", HistoryDetailRole.CHANNEL),
            ("03", HistoryDetailRole.ROW),
        ]

    def test_adjust_transpose_shows_signed_delta(self) -> None:
        controller = _controller()
        formatter = _formatter(controller)

        segments = formatter.adjust_transpose(0, GeneratorName.PULSE2, -3)

        assert _pairs(segments) == [
            ("00", HistoryDetailRole.FRAME),
            ("p", HistoryDetailRole.CHANNEL),
            ("00", HistoryDetailRole.ROW),
            ("-03", HistoryDetailRole.TRANSPOSE),
        ]


class TestOrderDetails:
    def test_add_frame_reports_the_landing_index(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.add_frame(2)) == [("03", HistoryDetailRole.FRAME)]

    def test_copy_frame_points_source_to_the_copy(self) -> None:
        """One builder serves both duplicating and cloning, since each lands a copy after its source."""
        formatter = _formatter(_controller())

        assert _pairs(formatter.copy_frame(2)) == [
            ("02", HistoryDetailRole.FRAME),
            (">", HistoryDetailRole.SEPARATOR),
            ("03", HistoryDetailRole.FRAME),
        ]

    def test_move_frame_shows_source_and_destination(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.move_frame(1, 3)) == [
            ("01", HistoryDetailRole.FRAME),
            (">", HistoryDetailRole.SEPARATOR),
            ("03", HistoryDetailRole.FRAME),
        ]

    def test_set_order_entry_maps_channel_to_pattern(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.set_order_entry(GeneratorName.PULSE1, 1, 5)) == [
            ("01", HistoryDetailRole.FRAME),
            ("P", HistoryDetailRole.CHANNEL),
            (">", HistoryDetailRole.SEPARATOR),
            ("05", HistoryDetailRole.VALUE),
        ]

    def test_set_master_entry_lists_every_channel(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.set_master_entry(1, 5)) == [
            ("01", HistoryDetailRole.FRAME),
            ("PpTN", HistoryDetailRole.CHANNEL),
            (">", HistoryDetailRole.SEPARATOR),
            ("05", HistoryDetailRole.VALUE),
        ]

    def test_a_block_reads_as_the_positions_and_the_channels_it_covers(self) -> None:
        formatter = _formatter(_controller())

        segments = formatter.order_block(
            OrderRegion(
                first_row=CHANNEL_AXIS.index(GeneratorName.PULSE2),
                last_row=CHANNEL_AXIS.index(GeneratorName.TRIANGLE),
                first_position=1,
                last_position=4,
            )
        )

        assert _pairs(segments) == [
            ("01-04", HistoryDetailRole.FRAME),
            ("pT", HistoryDetailRole.CHANNEL),
        ]

    def test_a_block_reaching_the_master_row_reads_as_every_channel(self) -> None:
        formatter = _formatter(_controller())

        segments = formatter.order_block(
            OrderRegion(
                first_row=CHANNEL_AXIS.index(None),
                last_row=CHANNEL_AXIS.index(None),
                first_position=2,
                last_position=2,
            )
        )

        assert _pairs(segments) == [
            ("02", HistoryDetailRole.FRAME),
            ("PpTN", HistoryDetailRole.CHANNEL),
        ]

    def test_a_paste_reads_as_the_cell_it_was_written_from(self) -> None:
        formatter = _formatter(_controller())

        segments = formatter.order_paste(OrderCell(generator=GeneratorName.NOISE, position=3))

        assert _pairs(segments) == [
            ("03", HistoryDetailRole.FRAME),
            ("N", HistoryDetailRole.CHANNEL),
        ]


class TestSampleDetails:
    def test_add_sample_shows_the_name(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.add_sample("Bass")) == [("Bass", HistoryDetailRole.NAME)]

    def test_remove_sample_shows_position_and_name(self) -> None:
        controller = _controller()
        sample = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        assert _pairs(formatter.remove_sample(sample.id)) == [
            ("00:", HistoryDetailRole.SAMPLE),
            ("Bass", HistoryDetailRole.NAME),
        ]

    def test_replace_sample_shows_position_and_both_names(self) -> None:
        controller = _controller()
        sample = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        assert _pairs(formatter.replace_sample(sample.id, "Kick")) == [
            ("00:", HistoryDetailRole.SAMPLE),
            ("Bass", HistoryDetailRole.NAME),
            (">", HistoryDetailRole.SEPARATOR),
            ("Kick", HistoryDetailRole.NAME),
        ]

    def test_rename_sample_shows_old_and_new(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.rename_sample("Bass", "Kick")) == [
            ("Bass", HistoryDetailRole.NAME),
            (">", HistoryDetailRole.SEPARATOR),
            ("Kick", HistoryDetailRole.NAME),
        ]

    def test_move_sample_shows_source_position_and_destination(self) -> None:
        controller = _controller()
        sample = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        assert _pairs(formatter.move_sample(sample.id, 5)) == [
            ("00", HistoryDetailRole.SAMPLE),
            (">", HistoryDetailRole.SEPARATOR),
            ("05", HistoryDetailRole.VALUE),
        ]

    def test_set_sample_loop_stores_the_state_as_a_word_key(self) -> None:
        controller = _controller()
        sample = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        on_segments = formatter.set_sample_loop(sample.id, True)
        off_segments = formatter.set_sample_loop(sample.id, False)

        assert on_segments[0] == HistoryDetailSegment(text="00:", role=HistoryDetailRole.SAMPLE)
        assert on_segments[1] == HistoryDetailWordSegment(
            word=HistoryDetailWord.LOOP_ON,
            role=HistoryDetailRole.VALUE,
        )
        assert off_segments[1] == HistoryDetailWordSegment(
            word=HistoryDetailWord.LOOP_OFF,
            role=HistoryDetailRole.VALUE,
        )

    def test_value_wraps_a_number(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.value(150)) == [("150", HistoryDetailRole.VALUE)]


class TestReconstructionDetails:
    def test_edit_reconstruction_names_position_channel_and_feature(self) -> None:
        controller = _controller()
        sample = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="lead")
        formatter = _formatter(controller)

        segments = formatter.edit_reconstruction(sample.id, GeneratorName.PULSE1, FeatureKey.VOLUME)

        assert _pairs(segments) == [
            ("00:", HistoryDetailRole.SAMPLE),
            ("P", HistoryDetailRole.CHANNEL),
            ("v", HistoryDetailRole.FEATURE_VOLUME),
        ]

    @pytest.mark.parametrize(
        ("feature_key", "letter", "role"),
        [
            (FeatureKey.INITIAL_PITCH, "i", HistoryDetailRole.FEATURE_PITCH),
            (FeatureKey.VOLUME, "v", HistoryDetailRole.FEATURE_VOLUME),
            (FeatureKey.ARPEGGIO, "a", HistoryDetailRole.FEATURE_ARPEGGIO),
            (FeatureKey.PITCH, "p", HistoryDetailRole.FEATURE_PITCH),
            (FeatureKey.HI_PITCH, "h", HistoryDetailRole.FEATURE_PITCH),
            (FeatureKey.DUTY_CYCLE, "d", HistoryDetailRole.FEATURE_DUTY_CYCLE),
        ],
    )
    def test_every_feature_has_a_letter_and_a_colour_role(
        self,
        feature_key: FeatureKey,
        letter: str,
        role: HistoryDetailRole,
    ) -> None:
        controller = _controller()
        sample = controller.add_sample(sample_reconstruction([GeneratorName.PULSE1]), name="lead")
        formatter = _formatter(controller)

        segments = formatter.edit_reconstruction(sample.id, GeneratorName.PULSE1, feature_key)

        assert (segments[-1].text, segments[-1].role) == (letter, role)
