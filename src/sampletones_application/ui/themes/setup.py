from pathlib import Path

from sampletones_application.ui.themes.loader import ThemeLoader
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.palette.palette import Palette


def setup_themes(theme_directory: Path, palette: Palette) -> None:
    for theme in ThemeLoader(theme_directory, palette).load_all():
        ThemeRegistry.register(theme)
