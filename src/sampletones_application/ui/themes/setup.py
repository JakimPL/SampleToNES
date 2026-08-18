from pathlib import Path

from sampletones_application.ui.themes.loader import ThemeLoader
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.palette.source import PaletteSource


def setup_themes(theme_directory: Path, palette_source: PaletteSource) -> None:
    for theme in ThemeLoader(theme_directory, palette_source).load_all():
        ThemeRegistry.register(theme)
