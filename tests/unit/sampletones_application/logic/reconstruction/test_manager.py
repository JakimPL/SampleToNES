from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import LoadReconstructionError


class TestLoadReconstructionPropagatesErrors:
    @staticmethod
    def _manager() -> ReconstructionManager:
        return ReconstructionManager(scheduling=MagicMock())

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            self._manager().load_reconstruction(tmp_path / "nope.stn")

    def test_directory_raises_is_a_directory(self, tmp_path: Path) -> None:
        with pytest.raises(IsADirectoryError):
            self._manager().load_reconstruction(tmp_path)

    def test_foreign_file_raises_load_reconstruction_error(self, tmp_path: Path) -> None:
        foreign = tmp_path / "kick.wav"
        foreign.write_bytes(b"RIFF\x58\xb9\x00\x00WAVEfmt " + b"\x00" * 256)

        with pytest.raises(LoadReconstructionError):
            self._manager().load_reconstruction(foreign)


class TestReconstructionManagerLoadReconstruction:
    def test_load_reconstruction_from_file_marks_session_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "song.stn"
        reconstruction_factory().save(save_path)
        reconstruction_manager.load_reconstruction(save_path)
        assert reconstruction_manager.session.is_loaded

    def test_load_reconstruction_from_file_fires_callback(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        save_path = tmp_path / "song.stn"
        reconstruction_factory().save(save_path)
        callback = MagicMock()
        reconstruction_manager.on_reconstruction_loaded = callback
        reconstruction_manager.load_reconstruction(save_path)
        callback.assert_called_once()


class TestReconstructionManagerSaveReconstruction:
    def test_save_with_explicit_path_saves_file(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        save_path = tmp_path / "saved.stn"
        reconstruction_manager.save_reconstruction(save_path)
        assert save_path.exists()

    def test_save_with_no_path_and_no_filepath_is_no_op(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        reconstruction_manager.save_reconstruction()

    def test_save_when_nothing_loaded_is_no_op(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        reconstruction_manager.save_reconstruction(tmp_path / "out.stn")


class TestReconstructionManagerLoadObject:
    def test_load_object_marks_session_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        assert reconstruction_manager.session.is_loaded

    def test_load_object_sets_current_reconstruction(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        assert reconstruction_manager.current_reconstruction is not None

    def test_load_object_sets_reconstruction_by_identity(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(reconstruction)
        assert reconstruction_manager.reconstruction is reconstruction

    def test_load_object_fires_on_reconstruction_loaded_callback(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        callback = MagicMock()
        reconstruction_manager.on_reconstruction_loaded = callback
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        callback.assert_called_once()


class TestReconstructionManagerClose:
    def test_close_resets_current_reconstruction_to_none(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        reconstruction_manager.close_reconstruction()
        assert reconstruction_manager.current_reconstruction is None

    def test_close_fires_on_reconstruction_closed_callback(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        callback = MagicMock()
        reconstruction_manager.on_reconstruction_closed = callback
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        reconstruction_manager.close_reconstruction()
        callback.assert_called_once()

    def test_close_marks_session_closed(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        reconstruction_manager.close_reconstruction()
        assert not reconstruction_manager.session.is_loaded

    def test_close_resets_audio_filepath_to_none(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        reconstruction_manager.close_reconstruction()
        assert reconstruction_manager.audio_filepath is None


class TestReconstructionManagerProperties:
    def test_reconstruction_property_returns_the_reconstruction_object(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(reconstruction)
        assert reconstruction_manager.reconstruction is reconstruction

    def test_filepath_property_is_none_for_in_memory_reconstruction(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        assert reconstruction_manager.filepath is None

    def test_audio_filepath_returns_reconstruction_audio_filepath(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction = reconstruction_factory()
        reconstruction_manager.load_reconstruction_object(reconstruction)
        assert reconstruction_manager.audio_filepath == reconstruction.audio_filepath

    def test_current_features_is_populated_after_load(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        assert reconstruction_manager.current_features is not None


class TestReconstructionManagerPropertiesWhenEmpty:
    def test_reconstruction_is_none_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert reconstruction_manager.reconstruction is None

    def test_filepath_is_none_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert reconstruction_manager.filepath is None

    def test_audio_filepath_is_none_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        assert reconstruction_manager.audio_filepath is None


class TestReconstructionManagerMarkUpdated:
    def test_mark_updated_sets_unsaved_changes(
        self,
        reconstruction_manager: ReconstructionManager,
        reconstruction_factory: Callable[[], Reconstruction],
    ) -> None:
        reconstruction_manager.load_reconstruction_object(reconstruction_factory())
        reconstruction_manager.mark_updated()
        assert reconstruction_manager.session.unsaved_changes


class TestReconstructionManagerInternalGuards:
    def test_load_features_without_reconstruction_raises_runtime_error(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        with pytest.raises(RuntimeError):
            reconstruction_manager._load_reconstruction_features()


class TestReconstructionManagerLocateOriginalAudio:
    def test_locate_audio_raises_file_not_found_when_audio_missing(
        self,
        reconstruction_manager: ReconstructionManager,
        tmp_path: Path,
    ) -> None:
        missing_path = tmp_path / "ghost.wav"
        reconstruction = Reconstruction.create(
            approximation=np.zeros(64, dtype=np.float32),
            approximations={GeneratorName.PULSE1: np.zeros(64, dtype=np.float32)},
            instructions={GeneratorName.PULSE1: [PulseInstruction(on=True, pitch=60, volume=8, duty_cycle=0)]},
            config=Config(),
            coefficient=1.0,
            audio_filepath=missing_path,
        )
        reconstruction_manager.load_reconstruction_object(reconstruction)
        with pytest.raises(FileNotFoundError):
            reconstruction_manager.locate_original_audio()

    def test_locate_audio_returns_silently_when_nothing_loaded(
        self,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        reconstruction_manager.locate_original_audio()
