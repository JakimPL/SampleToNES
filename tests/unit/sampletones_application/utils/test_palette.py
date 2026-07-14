from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from sampletones_application.utils.palette import (
    PALETTE_CONTEXT_KEY,
    Palette,
    PaletteColor,
    PaletteReference,
)


class _Swatch(BaseModel, frozen=True):
    color: PaletteColor


_PALETTE = """
name: test
colors:
  accent: "#a97fe3"
  overlay: "#ffffff40"
"""


class TestPaletteReference:
    def test_a_bare_token_carries_no_alpha_override(self) -> None:
        reference = PaletteReference.model_validate(".accent")
        assert reference.token == "accent"
        assert reference.alpha is None

    def test_a_token_with_alpha_captures_the_fraction(self) -> None:
        reference = PaletteReference.model_validate(".accent/0.5")
        assert reference.token == "accent"
        assert reference.alpha == 0.5

    def test_a_value_without_the_prefix_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            PaletteReference.model_validate("#a97fe3")

    def test_an_alpha_outside_the_unit_range_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            PaletteReference.model_validate(".accent/1.5")


class TestPaletteResolution:
    @pytest.fixture
    def palette(self) -> Palette:
        return Palette.model_validate({"name": "test", "colors": {"accent": "#a97fe3", "overlay": "#ffffff40"}})

    def test_a_reference_resolves_to_its_token_colour(self, palette: Palette) -> None:
        assert palette.resolve(PaletteReference(token="accent")) == (169, 127, 227, 255)

    def test_an_alpha_override_replaces_only_the_alpha_channel(self, palette: Palette) -> None:
        assert palette.resolve(PaletteReference(token="accent", alpha=0.5)) == (169, 127, 227, 128)

    def test_an_unknown_token_raises(self, palette: Palette) -> None:
        with pytest.raises(KeyError):
            palette.resolve(PaletteReference(token="missing"))


class TestLoadPalette:
    def test_a_present_palette_file_is_loaded(self, tmp_path: Path) -> None:
        palette_path = tmp_path / "palette.yaml"
        palette_path.write_text(_PALETTE)
        palette = Palette.load(palette_path)
        assert palette.resolve(PaletteReference(token="accent")) == (169, 127, 227, 255)

    def test_a_missing_palette_raises_system_error(self, tmp_path: Path) -> None:
        with pytest.raises(SystemError):
            Palette.load(tmp_path / "missing")


class TestPaletteColor:
    @pytest.fixture
    def palette(self) -> Palette:
        return Palette.model_validate({"name": "test", "colors": {"accent": "#a97fe3", "overlay": "#ffffff40"}})

    def test_a_hex_literal_resolves_without_a_palette(self) -> None:
        assert _Swatch.model_validate({"color": "#a97fe3"}).color == (169, 127, 227, 255)

    def test_a_reference_resolves_against_the_context_palette(self, palette: Palette) -> None:
        swatch = _Swatch.model_validate({"color": ".accent"}, context={PALETTE_CONTEXT_KEY: palette})
        assert swatch.color == (169, 127, 227, 255)

    def test_a_reference_alpha_override_is_applied(self, palette: Palette) -> None:
        swatch = _Swatch.model_validate({"color": ".accent/0.5"}, context={PALETTE_CONTEXT_KEY: palette})
        assert swatch.color == (169, 127, 227, 128)

    def test_a_reference_without_a_palette_context_raises(self) -> None:
        with pytest.raises(ValidationError):
            _Swatch.model_validate({"color": ".accent"})
