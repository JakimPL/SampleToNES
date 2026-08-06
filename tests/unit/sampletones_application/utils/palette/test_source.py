from typing import List

import pytest

from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource


@pytest.fixture
def studio() -> Palette:
    return Palette.model_validate({"name": "studio", "colors": {"accent": "#a97fe3"}})


@pytest.fixture
def light() -> Palette:
    return Palette.model_validate({"name": "light", "colors": {"accent": "#6b3fb0"}})


class TestActivate:
    def test_the_source_reports_the_palette_it_was_built_with(self, studio: Palette) -> None:
        source = PaletteSource(studio)

        assert source.palette is studio

    def test_activating_another_palette_replaces_the_one_in_place(
        self,
        studio: Palette,
        light: Palette,
    ) -> None:
        source = PaletteSource(studio)

        source.activate(light)

        assert source.palette is light

    def test_activating_announces_the_palette_now_in_place(
        self,
        studio: Palette,
        light: Palette,
    ) -> None:
        activated: List[Palette] = []
        source = PaletteSource(studio)
        source.on_palette_changed = activated.append

        source.activate(light)

        assert activated == [light]

    def test_activating_the_palette_in_place_announces_nothing(self, studio: Palette) -> None:
        activated: List[Palette] = []
        source = PaletteSource(studio)
        source.on_palette_changed = activated.append

        source.activate(studio)

        assert activated == []
