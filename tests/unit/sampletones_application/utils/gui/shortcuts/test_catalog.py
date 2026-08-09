from pathlib import Path

import pytest

from sampletones_application.constants.keybindings import DEFAULT_SCHEME_NAME
from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.shortcuts.catalog import ShortcutCatalog
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.paths import EXT_FILE_YAML

SHIPPED_FILE = KEYBINDINGS_DIRECTORY / f"{DEFAULT_SCHEME_NAME}{EXT_FILE_YAML}"
COMPACT_SCHEME_NAME = "compact"


def _named(name: str) -> str:
    """The shipped scheme written under another name, which is what a second scheme differs in."""
    return SHIPPED_FILE.read_text().replace(f"name: {DEFAULT_SCHEME_NAME}", f"name: {name}", 1)


@pytest.fixture
def directory(tmp_path: Path) -> Path:
    (tmp_path / f"{DEFAULT_SCHEME_NAME}{EXT_FILE_YAML}").write_text(SHIPPED_FILE.read_text())
    (tmp_path / f"{COMPACT_SCHEME_NAME}{EXT_FILE_YAML}").write_text(_named(COMPACT_SCHEME_NAME))
    return tmp_path


class TestLoadCatalog:
    def test_every_scheme_in_the_directory_is_indexed_by_name(self, directory: Path) -> None:
        assert ShortcutCatalog.load(directory).names == (COMPACT_SCHEME_NAME, DEFAULT_SCHEME_NAME)

    def test_an_empty_directory_raises_system_error(self, tmp_path: Path) -> None:
        with pytest.raises(SystemError):
            ShortcutCatalog.load(tmp_path)

    def test_a_directory_omitting_the_default_scheme_raises_system_error(self, tmp_path: Path) -> None:
        (tmp_path / f"{COMPACT_SCHEME_NAME}{EXT_FILE_YAML}").write_text(_named(COMPACT_SCHEME_NAME))

        with pytest.raises(SystemError):
            ShortcutCatalog.load(tmp_path)

    def test_a_scheme_named_apart_from_its_file_raises(self, directory: Path) -> None:
        (directory / f"tracker{EXT_FILE_YAML}").write_text(_named(COMPACT_SCHEME_NAME))

        with pytest.raises(ValueError):
            ShortcutCatalog.load(directory)


class TestSelectScheme:
    def test_a_known_name_selects_that_scheme(self, directory: Path) -> None:
        assert ShortcutCatalog.load(directory).select(COMPACT_SCHEME_NAME).name == COMPACT_SCHEME_NAME

    def test_an_unknown_name_falls_back_to_the_default(self, directory: Path) -> None:
        assert ShortcutCatalog.load(directory).select("vintage").name == DEFAULT_SCHEME_NAME

    def test_an_unknown_name_raises_when_looked_up_directly(self, directory: Path) -> None:
        with pytest.raises(KeyError):
            ShortcutCatalog.load(directory).get("vintage")


class TestShippedSchemes:
    def test_the_build_ships_a_default_scheme(self) -> None:
        """Loading is what proves every action is answered and no category holds a clash."""
        assert DEFAULT_SCHEME_NAME in ShortcutCatalog.load(KEYBINDINGS_DIRECTORY).names

    def test_the_shipped_scheme_answers_every_action(self) -> None:
        catalog = ShortcutCatalog.load(KEYBINDINGS_DIRECTORY)

        assert set(catalog.default.bindings) == set(ShortcutId)
