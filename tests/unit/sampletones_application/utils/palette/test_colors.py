import pytest

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.blended import BlendedColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.utils.palette.colors.grayscale import GrayscaleColor
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.utils.palette.colors.named import NamedColor
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.reference import PaletteReference
from sampletones_application.utils.palette.source import PaletteSource

BLACK = LiteralColor((0, 0, 0, 255))
WHITE = LiteralColor((255, 255, 255, 255))


@pytest.fixture
def accent(source: PaletteSource) -> BaseColor:
    return NamedColor(
        reference=PaletteReference(token="accent"),
        source=source,
    )


class TestComposedColor:
    """Fading, desaturating and mixing each answer with a colour that still reads the palette."""

    def test_fading_keeps_the_hue_and_sets_the_opacity(self, accent: BaseColor) -> None:
        assert FadedColor(color=accent, fraction=0.5).rgba == (169, 127, 227, 128)

    def test_desaturating_collapses_the_channels_to_one_luminance(self, accent: BaseColor) -> None:
        gray = round(0.299 * 169 + 0.587 * 127 + 0.114 * 227)

        assert GrayscaleColor(color=accent).rgba == (gray, gray, gray, 255)

    def test_mixing_lands_between_the_two_ends(self) -> None:
        assert BlendedColor(start=BLACK, end=WHITE, fraction=0.5).rgba == (128, 128, 128, 255)

    def test_a_composed_colour_answers_with_the_newly_activated_palette(
        self,
        source: PaletteSource,
        light: Palette,
        accent: BaseColor,
    ) -> None:
        faded = FadedColor(color=accent, fraction=0.5)

        source.activate(light)

        assert faded.rgba == (107, 63, 176, 128)

    def test_compositions_nest(
        self,
        source: PaletteSource,
        light: Palette,
        accent: BaseColor,
    ) -> None:
        dimmed = FadedColor(
            color=GrayscaleColor(color=accent),
            fraction=0.25,
        )

        source.activate(light)

        gray = round(0.299 * 107 + 0.587 * 63 + 0.114 * 176)
        assert dimmed.rgba == (gray, gray, gray, 64)

    def test_the_same_composition_of_the_same_colour_is_one_value(
        self,
        accent: BaseColor,
    ) -> None:
        """A theme cache keyed by colour holds one entry per shade the application draws."""
        assert {
            FadedColor(color=accent, fraction=0.5),
            FadedColor(color=accent, fraction=0.5),
            FadedColor(color=accent, fraction=0.25),
        } == {
            FadedColor(color=accent, fraction=0.5),
            FadedColor(color=accent, fraction=0.25),
        }

    def test_the_same_composition_of_two_colours_stays_two_values(
        self,
        accent: BaseColor,
    ) -> None:
        assert FadedColor(color=accent, fraction=0.5) != FadedColor(color=WHITE, fraction=0.5)
