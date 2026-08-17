from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Tuple

from sampletones_application.utils.palette.palette import Palette
from sampletones_shared.logger import logger
from sampletones_shared.paths.extensions import EXT_FILE_YAML

DEFAULT_PALETTE_NAME: Final[str] = "studio"


@dataclass(frozen=True)
class PaletteCatalog:
    """The palettes a build ships, indexed by name so a stored preference selects one.

    A palette file is named after the palette it holds, which makes the name a reader
    states in a preference the same name they find on disk.
    """

    palettes: Dict[str, Palette]

    @classmethod
    def load(cls, directory: Path) -> PaletteCatalog:
        """Load every palette the directory holds, ordered by name.

        Raises:
            SystemError: when the directory holds no palette, or omits the default one.
            ValueError: when a palette's name differs from its file stem.
        """
        palettes: Dict[str, Palette] = {}
        for path in sorted(directory.glob(f"*{EXT_FILE_YAML}")):
            palette = Palette.load(path)
            if palette.name != path.stem:
                raise ValueError(f"Palette file '{path}' holds palette {palette.name!r}; the two names must match")

            palettes[palette.name] = palette

        if not palettes:
            raise SystemError(f"Palette directory '{directory}' holds no palette")

        if DEFAULT_PALETTE_NAME not in palettes:
            raise SystemError(
                f"Palette directory '{directory}' omits the default palette {DEFAULT_PALETTE_NAME!r}. "
                f"Available palettes: {sorted(palettes)}"
            )

        return cls(palettes=dict(sorted(palettes.items())))

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(self.palettes)

    @property
    def default(self) -> Palette:
        return self.palettes[DEFAULT_PALETTE_NAME]

    def get(self, name: str) -> Palette:
        """The palette of the given name.

        Raises:
            KeyError: when the catalog holds no palette of that name.
        """
        if name not in self.palettes:
            raise KeyError(f"Unknown palette {name!r}. Available palettes: {sorted(self.palettes)}")

        return self.palettes[name]

    def select(self, name: str) -> Palette:
        """The palette a stored preference names, falling back to the default.

        A preference outlives the build that wrote it, so a name a later build stopped
        shipping resolves to the default and the application keeps its appearance.
        """
        if name not in self.palettes:
            logger.warning(f"Unknown palette {name!r}, falling back to {DEFAULT_PALETTE_NAME!r}")
            return self.default

        return self.palettes[name]
