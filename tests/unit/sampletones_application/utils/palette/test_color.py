import pytest
from pydantic import BaseModel, ValidationError

from sampletones_application.utils.palette.color import PALETTE_CONTEXT_KEY, PaletteColor
from sampletones_application.utils.palette.palette import Palette


class _Swatch(BaseModel, frozen=True):
    color: PaletteColor


@pytest.fixture
def palette() -> Palette:
    return Palette.model_validate({"name": "test", "colors": {"accent": "#a97fe3", "overlay": "#ffffff40"}})


class TestPaletteColor:
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

    def test_a_palette_context_of_the_wrong_type_raises(self) -> None:
        with pytest.raises(TypeError):
            _Swatch.model_validate({"color": ".accent"}, context={PALETTE_CONTEXT_KEY: "studio"})
