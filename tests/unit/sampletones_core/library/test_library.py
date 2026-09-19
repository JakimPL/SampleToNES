from pathlib import Path

import pytest

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.library.data import InstructionLibraryData
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.library.library import InstructionLibrary
from sampletones_core.library.state import LibraryState


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


class TestTheStateOfALibraryInTheCatalog:
    def test_a_library_never_saved_is_missing(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
    ) -> None:
        assert library.state(library_key) is LibraryState.MISSING

    def test_a_library_this_build_saved_is_current(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        assert library.state(library_key) is LibraryState.CURRENT


class TestInstructionLibrarySaveLoad:
    def test_save_and_load_round_trip(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
        empty_library_data: InstructionLibraryData,
    ) -> None:
        library.save_data(library_key, empty_library_data)
        reopened = InstructionLibrary(directory=library.directory)
        reopened.load_data(library_key)
        assert reopened.data[library_key].config == empty_library_data.config

    def test_get_path_includes_filename(
        self,
        library: InstructionLibrary,
        library_key: InstructionLibraryKey,
    ) -> None:
        path = library.get_path(library_key)
        assert path.name == library_key.filename
