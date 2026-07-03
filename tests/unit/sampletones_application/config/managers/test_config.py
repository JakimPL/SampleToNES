import json
from pathlib import Path

import pytest

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.outcome import (
    ConfigLoadFailure,
    ConfigLoadFailureReason,
    ConfigRecovered,
)
from sampletones_application.config.updates import (
    AdvancedSettingsUpdate,
    AudioSettingsUpdate,
    GenerationSettingsUpdate,
    LibrarySettingsUpdate,
)
from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorName, SpectrumMethod
from sampletones_core.library import InstructionLibraryKey


def _manager(path: Path) -> ConfigManager:
    return ConfigManager(path)


class TestConfigManagerInitialize:
    def test_nonexistent_path_loads_default_config(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        assert isinstance(manager.config, Config)

    def test_valid_config_file_is_loaded(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        Config().save(path)
        manager = _manager(path)
        assert isinstance(manager.config, Config)

    def test_directory_path_records_load_failure(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path)
        assert isinstance(manager.config, Config)
        [outcome] = manager.pending_load_outcomes
        assert isinstance(outcome, ConfigLoadFailure)
        assert outcome.reason is ConfigLoadFailureReason.LOAD_ERROR

    def test_unknown_field_records_recovery(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"unexpected_field": True}))
        manager = _manager(path)
        assert isinstance(manager.config, Config)
        [outcome] = manager.pending_load_outcomes
        assert isinstance(outcome, ConfigRecovered)

    def test_recovery_preserves_valid_settings_and_lists_dropped(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text(
            json.dumps(
                {
                    "library": {"sample_rate": 22050},
                    "generation": {"drive": -5.0},
                    "obsolete_field": 1,
                }
            )
        )
        manager = _manager(path)
        assert manager.config.library.sample_rate == 22050
        assert manager.config.generation.drive == Config().generation.drive
        [outcome] = manager.pending_load_outcomes
        assert isinstance(outcome, ConfigRecovered)
        dropped = set(outcome.dropped)
        assert ("generation", "drive") in dropped
        assert ("obsolete_field",) in dropped

    def test_config_without_metadata_recovers(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"library": {"sample_rate": 22050}}))
        manager = _manager(path)
        assert manager.config.library.sample_rate == 22050
        assert not any(isinstance(outcome, ConfigLoadFailure) for outcome in manager.pending_load_outcomes)

    def test_corrupt_json_resets_to_default_and_records_parse_failure(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text("{ not valid json {{")
        manager = _manager(path)
        assert isinstance(manager.config, Config)
        [outcome] = manager.pending_load_outcomes
        assert isinstance(outcome, ConfigLoadFailure)
        assert outcome.reason is ConfigLoadFailureReason.PARSE_ERROR


class TestConfigManagerSaveConfig:
    def test_save_config_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "saved.json"
        manager = _manager(tmp_path / "missing.json")
        manager.config_path = path
        manager.save_config()
        assert path.exists()

    def test_save_config_creates_missing_parent_directories(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "nested" / "dir" / "config.json"
        manager = _manager(tmp_path / "missing.json")
        manager.config_path = path
        manager.save_config()
        assert path.exists()


class TestConfigManagerCallbacks:
    def test_callback_fires_when_update_gui_called(
        self,
        tmp_path: Path,
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        fired: list[str] = []
        manager.add_config_change_callback(lambda: fired.append("changed"))
        manager.update_gui()
        assert fired == ["changed"]

    def test_multiple_callbacks_all_fire(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        fired: list[str] = []
        manager.add_config_change_callback(lambda: fired.append("a"))
        manager.add_config_change_callback(lambda: fired.append("b"))
        manager.update_gui()
        assert fired == ["a", "b"]


class TestConfigManagerApplySettings:
    def test_apply_audio_settings_updates_normalize(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        original_normalize = manager.config.general.normalize
        update = AudioSettingsUpdate(
            normalize=not original_normalize,
            quantize=False,
        )
        manager.apply_audio_settings(update)
        assert manager.config.general.normalize != original_normalize

    def test_apply_library_settings_updates_sample_rate(
        self,
        tmp_path: Path,
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        update = LibrarySettingsUpdate(
            sample_rate=22050,
            nes_frequency=60,
            spectrum_method=SpectrumMethod.CQT,
            transformation_gamma=2,
        )
        manager.apply_library_settings(update)
        assert manager.config.library.sample_rate == 22050
        assert manager.config.library.spectrum_method == SpectrumMethod.CQT

    def test_apply_generation_settings_updates_drive(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        update = GenerationSettingsUpdate(
            drive=0.5,
            generators=[GeneratorName.PULSE1],
        )
        manager.apply_generation_settings(update)
        assert manager.config.generation.drive == pytest.approx(0.5)

    def test_apply_advanced_settings_updates_library_directory(
        self,
        tmp_path: Path,
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        lib_dir = tmp_path / "lib"
        rec_dir = tmp_path / "rec"
        update = AdvancedSettingsUpdate(
            max_workers=2,
            library_directory=lib_dir,
            reconstructions_directory=rec_dir,
        )
        manager.apply_advanced_settings(update)
        assert manager.library_directory == lib_dir

    def test_apply_settings_fires_config_change_callbacks(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        fired: list[str] = []
        manager.add_config_change_callback(lambda: fired.append("changed"))
        update = AudioSettingsUpdate(normalize=True, quantize=False)
        manager.apply_audio_settings(update)
        assert fired == ["changed"]


class TestConfigManagerProperties:
    def test_key_property_returns_instruction_library_key(
        self,
        tmp_path: Path,
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        assert isinstance(manager.key, InstructionLibraryKey)

    def test_get_library_directory_returns_path(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        assert isinstance(manager.get_library_directory(), Path)

    def test_get_reconstructions_directory_returns_path(
        self,
        tmp_path: Path,
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        assert isinstance(manager.get_reconstructions_directory(), Path)

    def test_window_is_initialized(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        assert manager.window is not None
