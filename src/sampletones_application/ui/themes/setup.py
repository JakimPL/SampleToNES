from pathlib import Path

from sampletones_application.ui.themes.loader import ThemeLoader
from sampletones_application.ui.themes.registry import ThemeRegistry


def setup_themes(theme_directory: Path, palette_path: Path) -> None:
    for theme in ThemeLoader(theme_directory, palette_path).load_all():
        ThemeRegistry.register(theme)
