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
    channel = controller.project.song[generator]
    return channel.get_row(channel.order[0], row_index)


def _place_instrument(controller: ProjectController, generator: GeneratorName, sample_id: str) -> None:
    channel = controller.project.song[generator]
    controller.set_row(
        generator,
        channel.order[0],
        0,
        instrument=Instrument(sample_id=sample_id, generator_name=generator),
    )


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
            instrument = _row(controller, generator).instrument
            assert instrument is not None
            assert instrument.sample_id == sample.id
            assert instrument.generator_name == generator

        for generator in (GeneratorName.PULSE2, GeneratorName.NOISE):
            assert _row(controller, generator).instrument is None

    def test_clears_channels_the_new_sample_does_not_use(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        stale = controller.add_sample(_reconstruction([GeneratorName.PULSE2]), name="bass")
        channel = controller.project.song[GeneratorName.PULSE2]
        controller.set_row(
            GeneratorName.PULSE2,
            channel.order[0],
            0,
            instrument=Instrument(sample_id=stale.id, generator_name=GeneratorName.PULSE2),
            volume=15,
        )

        lead = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="lead")
        logic.set_sample_instrument(0, lead.id)

        assert _row(controller, GeneratorName.PULSE1).instrument is not None
        cleared = _row(controller, GeneratorName.PULSE2)
        assert cleared.instrument is None
        assert cleared.volume is None

    def test_none_sample_clears_the_whole_row(self) -> None:
        controller = _controller()
        logic = SequencerGridLogic(controller)
        sample = controller.add_sample(_reconstruction([GeneratorName.PULSE1]), name="lead")
        logic.set_sample_instrument(0, sample.id)

        logic.set_sample_instrument(0, None)

        for generator in GeneratorName.items():
            assert _row(controller, generator).instrument is None


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
        assert carrier.instrument is not None
        assert carrier.transpose == 5
        assert carrier.volume == 10

        synced = _row(controller, GeneratorName.TRIANGLE)
        assert synced.instrument is None
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
            assert row.instrument is None
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
            assert row.instrument is not None


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
