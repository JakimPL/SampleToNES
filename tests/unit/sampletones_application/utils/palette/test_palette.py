from pathlib import Path

import pytest

from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.reference import PaletteReference

_PALETTE = """
name: test
colors:
  accent: "#a97fe3"
  overlay: "#ffffff40"
"""


@pytest.fixture
def palette() -> Palette:
    return Palette.model_validate({"name": "test", "colors": {"accent": "#a97fe3", "overlay": "#ffffff40"}})


class TestPaletteResolution:
    def test_a_reference_resolves_to_its_token_colour(self, palette: Palette) -> None:
        assert palette.resolve(PaletteReference(token="accent")) == (169, 127, 227, 255)

    def test_an_alpha_override_replaces_only_the_alpha_channel(self, palette: Palette) -> None:
        assert palette.resolve(PaletteReference(token="accent", alpha=0.5)) == (
            169,
            127,
            227,
            128,
        )

    def test_an_unknown_token_raises(self, palette: Palette) -> None:
        with pytest.raises(KeyError):
            palette.resolve(PaletteReference(token="missing"))


class TestLoadPalette:
    def test_a_present_palette_file_is_loaded(self, tmp_path: Path) -> None:
        palette_path = tmp_path / "test.yaml"
        palette_path.write_text(_PALETTE)
        assert Palette.load(palette_path).resolve(PaletteReference(token="accent")) == (
            169,
            127,
            227,
            255,
        )

    def test_a_missing_palette_raises_system_error(self, tmp_path: Path) -> None:
        with pytest.raises(SystemError):
            Palette.load(tmp_path / "missing")

    def test_a_palette_file_holding_a_sequence_raises_type_error(self, tmp_path: Path) -> None:
        palette_path = tmp_path / "test.yaml"
        palette_path.write_text("- accent\n")
        with pytest.raises(TypeError):
            Palette.load(palette_path)
