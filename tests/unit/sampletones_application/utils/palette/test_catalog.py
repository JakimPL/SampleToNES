from pathlib import Path

import pytest

from sampletones_application.paths import PALETTES_DIRECTORY
from sampletones_application.utils.palette.catalog import (
    DEFAULT_PALETTE_NAME,
    PaletteCatalog,
)

_STUDIO = """
name: studio
colors:
  accent: "#a97fe3"
"""

_LIGHT = """
name: light
colors:
  accent: "#6b3fb0"
"""


@pytest.fixture
def directory(tmp_path: Path) -> Path:
    (tmp_path / f"{DEFAULT_PALETTE_NAME}.yaml").write_text(_STUDIO)
    (tmp_path / "light.yaml").write_text(_LIGHT)
    return tmp_path


class TestLoadCatalog:
    def test_every_palette_in_the_directory_is_indexed_by_name(self, directory: Path) -> None:
        assert PaletteCatalog.load(directory).names == ("light", DEFAULT_PALETTE_NAME)

    def test_an_empty_directory_raises_system_error(self, tmp_path: Path) -> None:
        with pytest.raises(SystemError):
            PaletteCatalog.load(tmp_path)

    def test_a_directory_omitting_the_default_palette_raises_system_error(self, tmp_path: Path) -> None:
        (tmp_path / "light.yaml").write_text(_LIGHT)
        with pytest.raises(SystemError):
            PaletteCatalog.load(tmp_path)

    def test_a_palette_named_apart_from_its_file_raises(self, directory: Path) -> None:
        (directory / "dark.yaml").write_text(_LIGHT)
        with pytest.raises(ValueError):
            PaletteCatalog.load(directory)


class TestSelectPalette:
    def test_a_known_name_selects_that_palette(self, directory: Path) -> None:
        assert PaletteCatalog.load(directory).select("light").name == "light"

    def test_an_unknown_name_falls_back_to_the_default(self, directory: Path) -> None:
        assert PaletteCatalog.load(directory).select("neon").name == DEFAULT_PALETTE_NAME

    def test_an_unknown_name_raises_when_looked_up_directly(self, directory: Path) -> None:
        with pytest.raises(KeyError):
            PaletteCatalog.load(directory).get("neon")


class TestShippedPalettes:
    """Every shipped palette must answer the same tokens.

    A layout or theme entry names one token and every palette resolves it, so a palette
    that omits a token fails at load in whichever file happens to reference it.
    """

    @pytest.fixture
    def catalog(self) -> PaletteCatalog:
        return PaletteCatalog.load(PALETTES_DIRECTORY)

    def test_the_default_palette_ships(self, catalog: PaletteCatalog) -> None:
        assert catalog.default.name == DEFAULT_PALETTE_NAME

    def test_every_palette_declares_the_same_tokens(self, catalog: PaletteCatalog) -> None:
        expected = set(catalog.default.colors)
        for name, palette in catalog.palettes.items():
            assert set(palette.colors) == expected, f"Palette {name!r} token set differs from {DEFAULT_PALETTE_NAME!r}"
