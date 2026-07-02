from pathlib import Path

import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.library.data import InstructionLibraryData
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.library.library import InstructionLibrary


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def window(config: Config) -> Window:
    return Window.from_config(config)


@pytest.fixture
def library(tmp_path: Path) -> InstructionLibrary:
    return InstructionLibrary(directory=str(tmp_path))


@pytest.fixture
def library_key(
    library: InstructionLibrary,
    config: Config,
    window: Window,
) -> InstructionLibraryKey:
    return library.create_key(config, window)


@pytest.fixture
def empty_library_data(config: Config) -> InstructionLibraryData:
    return InstructionLibraryData.create(config, {})


class TestInstructionLibraryFromConfig:
    def test_from_config_creates_instance(self, config: Config) -> None:
        library = InstructionLibrary.from_config(config)
        assert isinstance(library, InstructionLibrary)

    def test_from_config_uses_config_library_directory(
        self,
        config: Config,
    ) -> None:
        library = InstructionLibrary.from_config(config)
        assert str(config.general.library_directory) in library.directory

    def test_create_key_is_deterministic(
        self,
        library: InstructionLibrary,
        config: Config,
        window: Window,
    ) -> None:
        key1 = library.create_key(config, window)
        key2 = library.create_key(config, window)
        assert key1 == key2


class TestInstructionLibraryGet:
    def test_get_with_no_data_returns_none(
        self,
        library: InstructionLibrary,
        config: Config,
        window: Window,
    ) -> None:
        result = library.get(config, window)
        assert result is None

    def test_get_after_save_data_returns_data(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
        config: Config,
        window: Window,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        result = library.get(config, window)
        assert result is not None

    def test_get_without_window_defaults_from_config(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
        config: Config,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        result = library.get(config)
        assert result is not None


class TestInstructionLibraryExists:
    def test_exists_returns_false_before_save(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
    ) -> None:
        assert library.exists(library_key) is False

    def test_exists_returns_true_after_save(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        assert library.exists(library_key) is True

    def test_exists_with_config_resolves_key(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
        config: Config,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        assert library.exists(config) is True


class TestInstructionLibraryPurge:
    def test_purge_clears_in_memory_data(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        assert len(library.data) > 0
        library.purge()
        assert len(library.data) == 0


class TestInstructionLibraryViews:
    def test_keys_values_items_after_save(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        assert library_key in library.keys()
        assert empty_library_data in library.values()
        assert (library_key, empty_library_data) in library.items()


class TestInstructionLibrarySaveLoad:
    def test_save_and_load_round_trip(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        library.purge()
        assert library_key not in library.data
        library.load_data(library_key)
        assert library_key in library.data

    def test_getitem_after_load(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        loaded = library[library_key]
        assert isinstance(loaded, InstructionLibraryData)

    def test_get_path_includes_filename(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
    ) -> None:
        path = library.get_path(library_key)
        assert path.name == library_key.filename
