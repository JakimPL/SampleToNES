from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from sampletones_application.layout.fonts import FontsLayout
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.glyphs.glyphs import Glyphs
from sampletones_application.paths import LAYOUT_DIRECTORY, PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.colors.written import PALETTE_SOURCE_CONTEXT_KEY
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.utils.theme.catalog import ThemeSpecCatalog
from sampletones_shared.utils.serialization import load_yaml_model, load_yaml_model_dir


@dataclass(frozen=True)
class ApplicationDesign:
    """The application's design in one palette, as the configuration states it: the palette, the
    themes its widgets are bound to, the general layout, the font sizes and the glyphs.

    A page drawn from it wears what the application wears, read from the same files, so a
    change to the application's look reaches every page that is built afterwards.
    """

    palette: Palette
    themes: ThemeSpecCatalog
    general: GeneralLayout
    fonts: FontsLayout
    glyphs: Glyphs

    @classmethod
    def load(cls, palette_name: str) -> ApplicationDesign:
        """The design in the palette the application knows by ``palette_name``.

        Raises:
            KeyError: If the build ships no palette of that name.
        """
        palette = PaletteCatalog.load(PALETTES_DIRECTORY).get(palette_name)
        source = PaletteSource(palette)
        context: Dict[str, object] = {PALETTE_SOURCE_CONTEXT_KEY: source}
        return cls(
            palette=palette,
            themes=ThemeSpecCatalog.load(THEME_DIRECTORY, source),
            general=load_yaml_model_dir(LAYOUT_DIRECTORY / "general", GeneralLayout, context=context),
            fonts=load_yaml_model(LAYOUT_DIRECTORY / "fonts.yaml", FontsLayout, context=context),
            glyphs=load_yaml_model(LAYOUT_DIRECTORY / "glyphs.yaml", Glyphs, context=context),
        )

    @property
    def glyph_characters(self) -> str:
        """Every character the glyph catalog holds, each once, in a stable order."""
        characters: Dict[str, None] = {}
        for group in self.glyphs.model_dump().values():
            for glyph in group.values():
                characters.update(dict.fromkeys(glyph))

        return "".join(sorted(characters))


def palette_names() -> Tuple[str, ...]:
    """Every palette name a page may be drawn in, the application's own default among them."""
    return PaletteCatalog.load(PALETTES_DIRECTORY).names
