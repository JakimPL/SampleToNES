from pathlib import Path
from typing import Callable

import numpy as np

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project import ProjectContainer
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.reconstructions import Reconstruction


def _controller() -> ProjectController:
    return ProjectController(ProjectManager())


class TestInfoAndSettings:
    def test_set_title_updates_info_and_marks_dirty(self) -> None:
        controller = _controller()
        controller.set_title("Demo")
        assert controller.project.info.title == "Demo"
        assert controller._project_manager.is_dirty is True

    def test_settings_edits_apply(self) -> None:
        controller = _controller()
        controller.set_tempo(128)
        controller.set_speed(4)
        assert controller.project.settings.tempo == 128
        assert controller.project.settings.speed == 4

    def test_rows_per_pattern_resizes_all_patterns(self) -> None:
        controller = _controller()
        song = controller.project.song
        original_length = song.rows_per_pattern
        new_length = original_length + 16

        controller.set_rows_per_pattern(new_length)

        assert song.rows_per_pattern == new_length
        for channel in song.channels.values():
            for pattern in channel.patterns.values():
                assert pattern.length == new_length


class TestSamples:
    def test_add_sample_appends_and_emits(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        emitted: list[str] = []
        controller.on_samples_changed = lambda: emitted.append("samples")

        sample = controller.add_sample(reconstruction_factory(), name="lead")

        assert list(controller.project.samples) == [sample]
        assert controller.project.sample(sample.id) is sample
        assert emitted == ["samples"]

    def test_remove_sample_purges_row_references(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        song = controller.project.song
        pattern_id = song.order[0][GeneratorName.PULSE1]
        controller.set_row(
            GeneratorName.PULSE1,
            pattern_id,
            0,
            instrument=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
            volume=15,
        )

        controller.remove_sample(sample.id)

        assert controller.project.sample(sample.id) is None
        assert song.pattern(GeneratorName.PULSE1, pattern_id).rows[0].instrument is None


class TestSong:
    def test_set_row_replaces_row(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        song = controller.project.song
        pattern_id = song.order[0][GeneratorName.PULSE1]

        controller.set_row(
            GeneratorName.PULSE1,
            pattern_id,
            2,
            instrument=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
            transpose=0,
            volume=10,
        )

        row = song.pattern(GeneratorName.PULSE1, pattern_id).rows[2]
        assert row.instrument is not None
        assert row.instrument.sample_id == sample.id
        assert row.transpose == 0
        assert row.volume == 10

    def test_remove_pattern_drops_from_pool_and_nulls_order_references(self) -> None:
        controller = _controller()
        song = controller.project.song

        pattern_index = controller.add_pattern(GeneratorName.TRIANGLE)
        controller.append_frame()
        controller.set_order_entry(GeneratorName.TRIANGLE, 1, pattern_index)
        assert song.order[1][GeneratorName.TRIANGLE] == pattern_index
        assert song.pattern(GeneratorName.TRIANGLE, pattern_index) is not None

        controller.remove_pattern(GeneratorName.TRIANGLE, pattern_index)
        assert song.pattern(GeneratorName.TRIANGLE, pattern_index) is None
        assert song.order[1][GeneratorName.TRIANGLE] is None

    def test_move_frame_swaps_order_positions(self) -> None:
        controller = _controller()
        song = controller.project.song
        first_index = song.order[0][GeneratorName.PULSE2]
        second_index = controller.add_pattern(GeneratorName.PULSE2)
        controller.append_frame()
        controller.set_order_entry(GeneratorName.PULSE2, 1, second_index)

        controller.move_frame(0, 1)

        assert song.order[0][GeneratorName.PULSE2] == second_index
        assert song.order[1][GeneratorName.PULSE2] == first_index


class TestPersistenceRoundTrip:
    def test_controller_edits_survive_save_load(
        self, tmp_path: Path, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller = _controller()
        controller.set_title("Round")
        controller.set_tempo(96)
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        song = controller.project.song
        pattern_id = song.order[0][GeneratorName.PULSE1]
        controller.set_row(
            GeneratorName.PULSE1,
            pattern_id,
            0,
            instrument=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
            volume=12,
        )

        path = tmp_path / "round.stp"
        controller.save(path)
        loaded = ProjectContainer.load(path)

        assert loaded.info.title == "Round"
        assert loaded.settings.tempo == 96
        assert [stored.name for stored in loaded.samples] == ["lead"]
        loaded_row = loaded.song.pattern(GeneratorName.PULSE1, pattern_id).rows[0]
        assert loaded_row.instrument is not None
        assert loaded_row.instrument.sample_id == sample.id
        assert loaded_row.volume == 12


class TestLiveLinkedReconstruction:
    def test_sample_holds_reconstruction_by_reference(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller = _controller()
        reconstruction = reconstruction_factory()
        sample = controller.add_sample(reconstruction, name="lead")

        assert controller.project.sample(sample.id).reconstruction is reconstruction

    def test_in_place_reconstruction_edit_is_visible_through_project(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller = _controller()
        reconstruction = reconstruction_factory()
        sample = controller.add_sample(reconstruction, name="lead")

        new_instructions = [PulseInstruction(on=True, pitch=72, volume=15, duty_cycle=1)]
        reconstruction.update_generator_data(
            GeneratorName.PULSE1,
            new_instructions,
            np.zeros(64, dtype=np.float32),
        )

        stored = controller.project.sample(sample.id).reconstruction
        assert stored.get_generator_instructions(GeneratorName.PULSE1) == new_instructions
