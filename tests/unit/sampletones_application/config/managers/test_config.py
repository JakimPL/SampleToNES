import json
from pathlib import Path
from typing import Final, List, Optional

import pytest

from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.outcome import (
    ConfigLoadFailure,
    ConfigLoadFailureReason,
    ConfigRecovered,
)
from sampletones_application.view_model.main.updates import (
    AdvancedSettingsUpdate,
    AudioSettingsUpdate,
    LibrarySettingsUpdate,
)
from sampletones_core.configs import Config, InstructionsLibraryConfig, PitchRange
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft import Window
from sampletones_core.library import InstructionLibraryKey, create_key_from_filename
from sampletones_core.library.settings import LibrarySettings

OTHER_TUNING: Final[float] = 432.0
STORED_GAMMA: Final[int] = 50
LOSSY_NES_FREQUENCY: Final[int] = 221
STORED_MIN_PITCH: Final[int] = 40
STORED_MAX_PITCH: Final[int] = 90


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
                    "generation": {"decoder": {"top_k": 0}},
                    "obsolete_field": 1,
                }
            )
        )
        manager = _manager(path)
        assert manager.config.library.sample_rate == 22050
        assert manager.config.generation.decoder.top_k == Config().generation.decoder.top_k
        [outcome] = manager.pending_load_outcomes
        assert isinstance(outcome, ConfigRecovered)
        dropped = set(outcome.dropped)
        assert ("generation", "decoder", "top_k") in dropped
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
        fired: List[str] = []
        manager.add_config_change_callback(lambda: fired.append("changed"))
        manager.update_gui()
        assert fired == ["changed"]

    def test_multiple_callbacks_all_fire(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        fired: List[str] = []
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
        )
        manager.apply_library_settings(update)
        assert manager.config.library.sample_rate == 22050

    def test_apply_advanced_settings_updates_library_directory(
        self,
        tmp_path: Path,
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        lib_dir = tmp_path / "lib"
        rec_dir = tmp_path / "rec"
        update = AdvancedSettingsUpdate(
            max_workers=2,
            spectrum_method=SpectrumMethod.CQT,
            transformation_gamma=2,
            library_directory=lib_dir,
            reconstructions_directory=rec_dir,
        )
        manager.apply_advanced_settings(update)
        assert manager.library_directory == lib_dir
        assert manager.config.library.spectrum_method == SpectrumMethod.CQT

    def test_apply_settings_fires_config_change_callbacks(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        fired: List[str] = []
        manager.add_config_change_callback(lambda: fired.append("changed"))
        update = AudioSettingsUpdate(normalize=True, quantize=False)
        manager.apply_audio_settings(update)
        assert fired == ["changed"]


class TestApplyingTheSettingsOfALibrary:
    """Opening a library makes the settings it was built for the configuration's, so the
    configuration names the library's own file."""

    def test_the_settings_a_library_states_are_applied_whole(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        stored = _library_settings(manager).model_copy(update={"a4_frequency": OTHER_TUNING})
        key = _key_of(stored)

        manager.apply_library_config(key, _stated(stored))

        assert (manager.config.library, manager.key) == (stored, key)

    @pytest.mark.parametrize(
        "stored_tuning",
        [None, OTHER_TUNING],
        ids=["no settings stated", "settings naming another file"],
    )
    def test_the_filename_settings_stand_over_the_current_tuning(
        self,
        tmp_path: Path,
        stored_tuning: Optional[float],
    ) -> None:
        manager = _manager(tmp_path / "missing.json")
        named = _library_settings(manager)
        stored = None if stored_tuning is None else _stated(named.model_copy(update={"a4_frequency": stored_tuning}))

        manager.apply_library_config(_key_of(named), stored)

        assert manager.config.library == named

    @pytest.mark.parametrize("nes_frequency", [LOSSY_NES_FREQUENCY, LOSSY_NES_FREQUENCY - 1])
    def test_a_library_read_from_its_name_alone_keeps_the_frequency_the_name_states(
        self,
        tmp_path: Path,
        nes_frequency: int,
    ) -> None:
        """Two frequencies whose frame lengths round to one value name two libraries; the one named
        by its file is the one whose settings the configuration takes."""
        manager = _manager(tmp_path / "missing.json")
        named = _library_settings(manager).model_copy(update={"nes_frequency": nes_frequency})
        key = create_key_from_filename(_key_of(named).filename)

        manager.apply_library_config(key, None)

        assert manager.config.library.nes_frequency == nes_frequency
        assert manager.key.filename == key.filename

    def test_the_range_of_notes_a_library_states_is_applied_with_its_settings(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        stored = LibrarySettings(
            library=_library_settings(manager),
            pitch_range=PitchRange(min_pitch=STORED_MIN_PITCH, max_pitch=STORED_MAX_PITCH),
        )
        key = InstructionLibraryKey.create(stored, Window.from_config(stored.library))

        manager.apply_library_config(key, stored)

        assert manager.config.general.pitch_range == stored.pitch_range
        assert manager.key == key

    def test_a_stated_range_naming_another_file_leaves_the_current_range(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        current = manager.config.general.pitch_range
        named = _library_settings(manager)
        stated = LibrarySettings(
            library=named, pitch_range=PitchRange(min_pitch=STORED_MIN_PITCH, max_pitch=STORED_MAX_PITCH)
        )

        manager.apply_library_config(_key_of(named), stated)

        assert (manager.config.library, manager.config.general.pitch_range) == (named, current)


class TestApplyingALibraryWrittenBeforeTheRangeJoinedItsSettings:
    """A release before library data version 2.2 named a library by its library section alone, so the
    section it states, tuning included, is applied whole to the range of notes in place."""

    @staticmethod
    def _legacy_key(library_config: InstructionsLibraryConfig) -> InstructionLibraryKey:
        filename = InstructionLibraryKey.library_only_filename(library_config, Window.from_config(library_config))
        return create_key_from_filename(filename)

    def test_its_tuning_is_applied_with_the_rest_of_its_section(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        current = manager.config.general.pitch_range
        stored = _library_settings(manager).model_copy(update={"a4_frequency": OTHER_TUNING})

        manager.apply_library_config(self._legacy_key(stored), LibrarySettings(library=stored, pitch_range=current))

        assert (manager.config.library, manager.config.general.pitch_range) == (stored, current)

    def test_a_section_naming_another_legacy_file_gives_way_to_the_filename(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        named = _library_settings(manager)
        stored = named.model_copy(update={"a4_frequency": OTHER_TUNING, "transformation_gamma": STORED_GAMMA + 1})

        manager.apply_library_config(
            self._legacy_key(named), LibrarySettings(library=stored, pitch_range=manager.config.general.pitch_range)
        )

        assert manager.config.library == named

    def test_the_rebuilt_library_takes_the_name_a_library_takes_now(self, tmp_path: Path) -> None:
        manager = _manager(tmp_path / "missing.json")
        stored = _library_settings(manager).model_copy(update={"a4_frequency": OTHER_TUNING})
        legacy = self._legacy_key(stored)

        manager.apply_library_config(
            legacy, LibrarySettings(library=stored, pitch_range=manager.config.general.pitch_range)
        )

        assert manager.key.filename != legacy.filename
        assert manager.key == _key_of(stored)


def _stated(library_config: InstructionsLibraryConfig) -> LibrarySettings:
    return LibrarySettings(library=library_config, pitch_range=Config().general.pitch_range)


def _library_settings(manager: ConfigManager) -> InstructionsLibraryConfig:
    """Library settings the manager's configuration differs from, at the manager's own tuning."""
    return manager.config.library.model_copy(
        update={"spectrum_method": SpectrumMethod.FFT, "transformation_gamma": STORED_GAMMA}
    )


def _key_of(library_config: InstructionsLibraryConfig) -> InstructionLibraryKey:
    """The key of a library built under ``library_config`` for the notes a default configuration covers."""
    settings = LibrarySettings(library=library_config, pitch_range=Config().general.pitch_range)
    return InstructionLibraryKey.create(settings, Window.from_config(library_config))


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
