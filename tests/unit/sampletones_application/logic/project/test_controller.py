from pathlib import Path
from typing import Callable, List

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
        emitted: List[str] = []
        controller.on_samples_changed = lambda: emitted.append("samples")

        sample = controller.add_sample(reconstruction_factory(), name="lead")

        assert list(controller.project.samples) == [sample]
        assert controller.project.sample(sample.id) is sample
        assert emitted == ["samples"]

    def test_add_sample_detaches_source_but_keeps_object_identity(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller = _controller()
        reconstruction = reconstruction_factory()
        assert reconstruction.audio_filepath is not None

        sample = controller.add_sample(reconstruction, name="lead")

        assert sample.reconstruction is reconstruction
        assert sample.reconstruction.audio_filepath is None

    def test_remove_sample_purges_row_references(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        song = controller.project.song
        pattern_id = song.order[0][GeneratorName.PULSE1]
        controller.set_row(
            GeneratorName.PULSE1,
            pattern_id,
            0,
            command=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
            volume=15,
        )

        controller.remove_sample(sample.id)

        assert controller.project.sample(sample.id) is None
        assert song.pattern(GeneratorName.PULSE1, pattern_id).rows[0].command is None

    def test_is_sample_used_reflects_pattern_references(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        pattern_id = controller.project.song.order[0][GeneratorName.PULSE1]

        assert controller.is_sample_used(sample.id) is False

        controller.set_row(
            GeneratorName.PULSE1,
            pattern_id,
            0,
            command=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
        )

        assert controller.is_sample_used(sample.id) is True

    def test_move_sample_reorders_pool(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        first = controller.add_sample(reconstruction_factory(), name="first")
        controller.add_sample(reconstruction_factory(), name="second")
        controller.add_sample(reconstruction_factory(), name="third")

        controller.move_sample(first.id, 2)

        assert [sample.name for sample in controller.project.samples] == ["second", "third", "first"]
        assert controller.project.samples.get_index(first.id) == 2

    def test_move_sample_preserves_row_references(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        controller.add_sample(reconstruction_factory(), name="pad")
        song = controller.project.song
        pattern_id = song.order[0][GeneratorName.PULSE1]
        controller.set_row(
            GeneratorName.PULSE1,
            pattern_id,
            0,
            command=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
        )

        controller.move_sample(sample.id, 1)

        row = song.pattern(GeneratorName.PULSE1, pattern_id).rows[0]
        assert row.command is not None
        assert row.command.sample_id == sample.id

    def test_move_sample_emits_samples_and_song_changes(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        controller.add_sample(reconstruction_factory(), name="pad")
        emitted: List[str] = []
        controller.on_samples_changed = lambda: emitted.append("samples")
        controller.on_song_changed = lambda: emitted.append("song")

        controller.move_sample(sample.id, 1)

        assert "samples" in emitted
        assert "song" in emitted

    def test_duplicate_sample_appends_independent_copy(
        self, reconstruction_factory: Callable[[], Reconstruction]
    ) -> None:
        controller = _controller()
        source = controller.add_sample(reconstruction_factory(), name="lead")

        clone = controller.duplicate_sample(source.id)

        assert clone.id != source.id
        assert clone.name == source.name
        assert clone.reconstruction is not source.reconstruction
        assert [sample.name for sample in controller.project.samples] == ["lead", "lead"]
        assert controller.project.samples.get_index(clone.id) == 1

    def test_duplicate_sample_emits_samples_change(self, reconstruction_factory: Callable[[], Reconstruction]) -> None:
        controller = _controller()
        source = controller.add_sample(reconstruction_factory(), name="lead")
        emitted: List[str] = []
        controller.on_samples_changed = lambda: emitted.append("samples")

        controller.duplicate_sample(source.id)

        assert emitted == ["samples"]


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
            command=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
            transpose=0,
            volume=10,
        )

        row = song.pattern(GeneratorName.PULSE1, pattern_id).rows[2]
        assert row.command is not None
        assert row.command.sample_id == sample.id
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
            command=Instrument(sample_id=sample.id, generator_name=GeneratorName.PULSE1),
            volume=12,
        )

        path = tmp_path / "round.stp"
        controller.save(path)
        loaded = ProjectContainer.load(path)

        assert loaded.info.title == "Round"
        assert loaded.settings.tempo == 96
        assert [stored.name for stored in loaded.samples] == ["lead"]
        loaded_row = loaded.song.pattern(GeneratorName.PULSE1, pattern_id).rows[0]
        assert loaded_row.command is not None
        assert loaded_row.command.sample_id == sample.id
        assert loaded_row.volume == 12


class TestProperties:
    def test_order_length_returns_number_of_frames(self) -> None:
        controller = _controller()
        assert controller.order_length >= 1

    def test_is_dirty_false_initially(self) -> None:
        controller = _controller()
        assert controller.is_dirty is False

    def test_is_dirty_true_after_mutation(self) -> None:
        controller = _controller()
        controller.set_title("x")
        assert controller.is_dirty is True


class TestProjectLifecycle:
    def test_new_creates_fresh_project_and_fires_callback(self) -> None:
        controller = _controller()
        controller.set_title("Before")
        fired: List[str] = []
        controller.on_project_replaced = lambda: fired.append("replaced")
        controller.new()
        assert controller.project.info.title == ""
        assert fired == ["replaced"]

    def test_close_fires_project_replaced_callback(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_project_replaced = lambda: fired.append("replaced")
        controller.close()
        assert fired == ["replaced"]

    def test_load_project_from_file(self, tmp_path: Path) -> None:
        source = _controller()
        source.set_title("Loaded")
        path = tmp_path / "project.stp"
        source.save(path)

        target = _controller()
        fired: List[str] = []
        target.on_project_replaced = lambda: fired.append("replaced")
        target.load(path)
        assert target.project.info.title == "Loaded"
        assert fired == ["replaced"]

    def test_mark_updated_fires_song_changed_callback(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_song_changed = lambda: fired.append("song")
        controller.mark_updated()
        assert fired == ["song"]


class TestInfoAndSettingsCallbacks:
    def test_set_author_updates_info_and_fires_callback(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_info_changed = lambda: fired.append("info")
        controller.set_author("Alice")
        assert controller.project.info.author == "Alice"
        assert fired == ["info"]

    def test_set_comment_updates_info_and_fires_callback(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_info_changed = lambda: fired.append("info")
        controller.set_comment("A demo")
        assert controller.project.info.comment == "A demo"
        assert fired == ["info"]

    def test_set_tempo_fires_settings_callback(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_settings_changed = lambda: fired.append("settings")
        controller.set_tempo(120)
        assert fired == ["settings"]

    def test_set_speed_fires_settings_callback(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_settings_changed = lambda: fired.append("settings")
        controller.set_speed(6)
        assert fired == ["settings"]

    def test_set_nes_frequency_updates_settings(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_settings_changed = lambda: fired.append("settings")
        controller.set_nes_frequency(50)
        assert controller.project.settings.nes_frequency == 50
        assert fired == ["settings"]

    def test_set_sample_rate_updates_settings(self) -> None:
        controller = _controller()
        fired: List[str] = []
        controller.on_settings_changed = lambda: fired.append("settings")
        controller.set_sample_rate(44100)
        assert controller.project.settings.sample_rate == 44100
        assert fired == ["settings"]


class TestSampleLoop:
    def test_set_sample_loop_toggles_loop_flag(
        self,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        controller = _controller()
        sample = controller.add_sample(reconstruction_factory(), name="lead")
        controller.set_sample_loop(sample.id, True)
        assert controller.project.sample(sample.id).loop is True


class TestPatternManagement:
    def test_add_pattern_returns_int_index(self) -> None:
        controller = _controller()
        index = controller.add_pattern(GeneratorName.PULSE1)
        assert isinstance(index, int)

    def test_duplicate_pattern_creates_independent_copy(self) -> None:
        controller = _controller()
        original_index = controller.add_pattern(GeneratorName.TRIANGLE)
        clone_index = controller.duplicate_pattern(
            GeneratorName.TRIANGLE,
            original_index,
        )
        assert clone_index != original_index
        assert controller.song.pattern(GeneratorName.TRIANGLE, clone_index) is not None


class TestFrameManagement:
    def test_insert_frame_inserts_at_given_position(self) -> None:
        controller = _controller()
        controller.append_frame()
        initial_length = controller.order_length
        controller.insert_frame(0)
        assert controller.order_length == initial_length + 1


class TestExistingRow:
    def test_update_row_on_nonexistent_pattern_is_no_op(self) -> None:
        controller = _controller()
        controller.update_row(
            GeneratorName.PULSE1,
            999,
            0,
        )


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

        new_instructions = [
            PulseInstruction(
                on=True,
                pitch=72,
                volume=15,
                duty_cycle=1,
            )
        ]
        reconstruction.update_generator_data(
            GeneratorName.PULSE1,
            new_instructions,
            np.zeros(64, dtype=np.float32),
        )

        stored = controller.project.sample(sample.id).reconstruction
        assert stored.get_generator_instructions(GeneratorName.PULSE1) == new_instructions
