import pytest
from pydantic import BaseModel, ValidationError

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.utils.palette.colors.written import (
    PALETTE_SOURCE_CONTEXT_KEY,
    WrittenColor,
)
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource


class _Swatch(BaseModel, frozen=True):
    color: WrittenColor


def _swatch(written: object, source: PaletteSource) -> _Swatch:
    return _Swatch.model_validate({"color": written}, context={PALETTE_SOURCE_CONTEXT_KEY: source})


class TestWrittenColor:
    def test_a_hex_literal_resolves_without_a_palette(self) -> None:
        assert _Swatch.model_validate({"color": "#a97fe3"}).color.rgba == (169, 127, 227, 255)

    def test_a_reference_resolves_against_the_source_palette(self, source: PaletteSource) -> None:
        assert _swatch(".accent", source).color.rgba == (169, 127, 227, 255)

    def test_a_reference_alpha_override_is_applied(self, source: PaletteSource) -> None:
        assert _swatch(".accent/0.5", source).color.rgba == (169, 127, 227, 128)

    def test_a_colour_built_in_code_stands_as_it_is(self, source: PaletteSource) -> None:
        """A derived shade reaches a field as the colour it already is."""
        color: BaseColor = FadedColor(
            color=LiteralColor((240, 146, 86, 255)),
            fraction=0.5,
        )

        assert _swatch(color, source).color is color

    def test_a_value_of_another_kind_raises(self, source: PaletteSource) -> None:
        with pytest.raises(ValidationError):
            _swatch(42, source)

    def test_a_reference_without_a_palette_source_context_raises(self) -> None:
        with pytest.raises(ValidationError):
            _Swatch.model_validate({"color": ".accent"})

    def test_a_palette_source_context_of_the_wrong_type_raises(self, studio: Palette) -> None:
        with pytest.raises(TypeError):
            _Swatch.model_validate({"color": ".accent"}, context={PALETTE_SOURCE_CONTEXT_KEY: studio})

    def test_a_token_the_palette_in_place_omits_raises_at_load(self, source: PaletteSource) -> None:
        with pytest.raises(KeyError):
            _swatch(".missing", source)


class TestActivatedPalette:
    """A reference is read at the moment it is drawn with, so a swap needs no reload."""

    def test_a_reference_answers_with_the_newly_activated_palette(
        self,
        source: PaletteSource,
        light: Palette,
    ) -> None:
        swatch = _swatch(".accent", source)

        source.activate(light)

        assert swatch.color.rgba == (107, 63, 176, 255)

    def test_an_alpha_override_survives_the_swap(self, source: PaletteSource, light: Palette) -> None:
        swatch = _swatch(".accent/0.5", source)

        source.activate(light)

        assert swatch.color.rgba == (107, 63, 176, 128)

    def test_a_literal_stands_apart_from_the_palette(self, source: PaletteSource, light: Palette) -> None:
        swatch = _swatch("#a97fe3", source)

        source.activate(light)

        assert swatch.color.rgba == (169, 127, 227, 255)
