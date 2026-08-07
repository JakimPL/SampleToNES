import pytest

from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource


@pytest.fixture
def studio() -> Palette:
    return Palette.model_validate({"name": "studio", "colors": {"accent": "#a97fe3"}})


@pytest.fixture
def light() -> Palette:
    return Palette.model_validate({"name": "light", "colors": {"accent": "#6b3fb0"}})


@pytest.fixture
def source(studio: Palette) -> PaletteSource:
    return PaletteSource(studio)
