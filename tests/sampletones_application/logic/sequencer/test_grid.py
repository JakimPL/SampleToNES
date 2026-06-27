from pathlib import Path
from typing import List

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.grid import SequencerGridLogic
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.constants.symbols import MIXED

_LENGTH = 64


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


def _row(controller: ProjectController, generator: GeneratorName, row_index: int = 0) -> Row:
    song = controller.project.song
    pattern_index = song.order[0][generator]
    return song[generator].get_row(pattern_index, row_index)


def _place_instrument(controller: ProjectController, generator: GeneratorName, sample_id: str) -> None:
    pattern_index = controller.project.song.order[0][generator]
    controller.set_row(
        generator,
        pattern_index,
        0,
        command=Instrument(sample_id=sample_id, generator_name=generator),
    )


class TestSetNoteOff:
    def test_set_note_off_writes_note_off_command(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)

        logic.set_note_off(GeneratorName.PULSE1, 0)

        assert isinstance(_row(controller, GeneratorName.PULSE1).command, NoteOff)

    def test_set_note_off_all_generators_cuts_every_channel(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)

        logic.set_note_off_all_generators(0)

        for generator in GeneratorName.items():
            assert isinstance(_row(controller, generator).command, NoteOff)


class TestSetSampleInstrument:
    def test_fills_only_used_generators(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )

        logic.set_sample_instrument(0, sample.id)

        for generator in (GeneratorName.PULSE1, GeneratorName.TRIANGLE):
            command = _row(controller, generator).command
            assert command is not None
            assert command.sample_id == sample.id
            assert command.generator_name == generator

        for generator in (GeneratorName.PULSE2, GeneratorName.NOISE):
            assert _row(controller, generator).command is None

    def test_clears_channels_the_new_sample_does_not_use(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        stale = controller.add_sample(_reconstruction([GeneratorName.PULSE2]), name="bass")
        pattern_index = controller.project.song.order[0][GeneratorName.PULSE2]
        controller.set_row(
            GeneratorName.PULSE2,
            pattern_index,
            0,
            command=Instrument(sample_id=stale.id, generator_name=GeneratorName.PULSE2),
            volume=15,
        )

        lead = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="lead")
        logic.set_sample_instrument(0, lead.id)

        assert _row(controller, GeneratorName.PULSE1).command is not None
        cleared = _row(controller, GeneratorName.PULSE2)
        assert cleared.command is None
        assert cleared.volume is None

    def test_none_sample_clears_the_whole_row(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="lead")
        logic.set_sample_instrument(0, sample.id)

        logic.set_sample_instrument(0, None)

        for generator in GeneratorName.items():
            assert _row(controller, generator).command is None


class TestSampleSubcolumn:
    def test_synchronises_across_relevant_channels_even_without_instrument(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        _place_instrument(controller, GeneratorName.PULSE1, sample.id)

        logic.set_sample_subcolumn(0, transpose=5)
        logic.set_sample_subcolumn(0, volume=10)

        carrier = _row(controller, GeneratorName.PULSE1)
        assert carrier.command is not None
        assert carrier.transpose == 5
        assert carrier.volume == 10

        synced = _row(controller, GeneratorName.TRIANGLE)
        assert synced.command is None
        assert synced.transpose == 5
        assert synced.volume == 10

        for generator in (GeneratorName.PULSE2, GeneratorName.NOISE):
            row = _row(controller, generator)
            assert row.transpose is None
            assert row.volume is None

    def test_synchronises_across_all_channels_when_no_sample_is_referenced(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)

        logic.set_sample_subcolumn(0, transpose=5, volume=10)

        for generator in GeneratorName.items():
            row = _row(controller, generator)
            assert row.command is None
            assert row.transpose == 5
            assert row.volume == 10

    def test_clear_removes_one_subcolumn_across_relevant_channels(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_sample_subcolumn(0, transpose=5)
        logic.set_sample_subcolumn(0, volume=10)

        logic.clear_sample_subcolumn(0, transpose=True)

        for generator in (GeneratorName.PULSE1, GeneratorName.TRIANGLE):
            row = _row(controller, generator)
            assert row.transpose is None
            assert row.volume == 10
            assert row.command is not None


class TestBuildGridAggregation:
    def test_single_channel_of_a_multi_channel_sample_reads_mixed(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        _place_instrument(controller, GeneratorName.PULSE1, sample.id)

        row = logic.build_grid().rows[0]

        assert row.sample_instrument == MIXED

    def test_full_placement_reads_as_the_sample(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)

        row = logic.build_grid().rows[0]

        assert row.sample_instrument == row.cells[GeneratorName.PULSE1].instrument
        assert row.sample_instrument != MIXED

    def test_diverging_transpose_renders_as_mixed(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_row(GeneratorName.PULSE1, 0, transpose=5)

        row = logic.build_grid().rows[0]

        assert row.sample_transpose == MIXED

    def test_shared_transpose_is_reflected_in_the_sample_column(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(
            _reconstruction([GeneratorName.PULSE1, GeneratorName.TRIANGLE]),
            name="lead",
        )
        logic.set_sample_instrument(0, sample.id)
        logic.set_sample_subcolumn(0, transpose=5)

        row = logic.build_grid().rows[0]

        assert row.sample_transpose == row.cells[GeneratorName.PULSE1].transpose
        assert row.sample_transpose != MIXED


class TestEmptyFrameAutoCreate:
    def _append_empty_frame(self, controller: ProjectController) -> None:
        controller.append_frame()

    def test_editing_an_empty_slot_creates_and_assigns_a_pattern(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        self._append_empty_frame(controller)
        logic.select_frame(1)

        logic.set_row(GeneratorName.PULSE1, 0, transpose=5)

        song = controller.project.song
        new_index = song.order[1][GeneratorName.PULSE1]
        assert new_index is not None
        assert song[GeneratorName.PULSE1].get_row(new_index, 0).transpose == 5
        assert song.order[1][GeneratorName.PULSE2] is None

    def test_empty_frame_still_shows_editable_rows(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        self._append_empty_frame(controller)
        logic.select_frame(1)

        grid = logic.build_grid()

        assert len(grid.rows) == controller.project.song.rows_per_pattern
