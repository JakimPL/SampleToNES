from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock

import numpy as np

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_application.logic.sequencer.history_detail import SequencerHistoryDetail
from sampletones_application.logic.sequencer.samples import SequencerSamplesLogic
from sampletones_application.paths import LANG_EN
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.shared.history import HistoryDetailRole, HistoryDetailSegment
from sampletones_core.configs import Config
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction

_LENGTH = 64

Pair = Tuple[str, HistoryDetailRole]


def _controller() -> ProjectController:
    return ProjectController(ProjectManager())


def _reconstruction(generators: List[GeneratorName]) -> Reconstruction:
    instructions = {
        generator: [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)] for generator in generators
    }
    approximations = {generator: np.zeros(_LENGTH, dtype=np.float32) for generator in generators}
    return Reconstruction.create(
        approximation=np.zeros(_LENGTH, dtype=np.float32),
        approximations=approximations,
        instructions=instructions,
        config=Config(),
        coefficient=1.0,
        audio_filepath=Path("/dev/null"),
    )


def _formatter(controller: ProjectController) -> SequencerHistoryDetail:
    grid_logic = SequencerGridLogic(controller)
    samples_logic = SequencerSamplesLogic(
        controller,
        MagicMock(),
        MagicMock(),
        scheduling=MagicMock(),
    )
    return SequencerHistoryDetail(
        grid_logic,
        samples_logic,
        language_manager=LanguageManager(LANG_EN),
    )


def _pairs(segments: Tuple[HistoryDetailSegment, ...]) -> List[Pair]:
    return [(segment.text, segment.role) for segment in segments]


class TestGridDetails:
    def test_edit_row_single_channel_places_sample(self) -> None:
        controller = _controller()
        controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="lead")
        target = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="bass")
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
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE, GeneratorName.NOISE]),
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

    def test_duplicate_frame_points_source_to_the_copy(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.duplicate_frame(2)) == [
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


class TestSampleDetails:
    def test_add_sample_shows_the_name(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.add_sample("Bass")) == [("Bass", HistoryDetailRole.NAME)]

    def test_remove_sample_shows_position_and_name(self) -> None:
        controller = _controller()
        sample = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        assert _pairs(formatter.remove_sample(sample.id)) == [
            ("00:", HistoryDetailRole.SAMPLE),
            ("Bass", HistoryDetailRole.NAME),
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
        sample = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        assert _pairs(formatter.move_sample(sample.id, 5)) == [
            ("00", HistoryDetailRole.SAMPLE),
            (">", HistoryDetailRole.SEPARATOR),
            ("05", HistoryDetailRole.VALUE),
        ]

    def test_set_sample_loop_shows_resulting_state(self) -> None:
        controller = _controller()
        sample = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="Bass")
        formatter = _formatter(controller)

        on_segments = _pairs(formatter.set_sample_loop(sample.id, True))
        off_segments = _pairs(formatter.set_sample_loop(sample.id, False))

        assert on_segments[0] == ("00:", HistoryDetailRole.SAMPLE)
        assert on_segments[1][1] is HistoryDetailRole.VALUE
        assert off_segments[1][1] is HistoryDetailRole.VALUE
        assert on_segments[1][0] != off_segments[1][0]

    def test_value_wraps_a_number(self) -> None:
        formatter = _formatter(_controller())

        assert _pairs(formatter.value(150)) == [("150", HistoryDetailRole.VALUE)]


class TestReconstructionDetails:
    def test_edit_reconstruction_names_position_channel_and_feature(self) -> None:
        controller = _controller()
        sample = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="lead")
        formatter = _formatter(controller)

        segments = formatter.edit_reconstruction(sample.id, GeneratorName.PULSE1, FeatureKey.VOLUME)

        assert _pairs(segments) == [
            ("00:", HistoryDetailRole.SAMPLE),
            ("Pulse 1", HistoryDetailRole.CHANNEL),
            ("Volume", HistoryDetailRole.FEATURE),
        ]
