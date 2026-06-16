from pathlib import Path

from sampletones_application.ui.themes.loader import ThemeLoader
from sampletones_application.ui.themes.registry import ThemeRegistry


def setup_themes(theme_directory: Path) -> None:
    for theme in ThemeLoader(theme_directory).load_all():
        ThemeRegistry.register(theme)
