from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Tuple

from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_core.paths import EXT_FILE_YAML
from sampletones_shared.logger import logger

DEFAULT_SCHEME_NAME: Final[str] = "default"


@dataclass(frozen=True)
class ShortcutCatalog:
    """The keybinding schemes a build ships, indexed by name so a stored preference selects one.

    A scheme file is named after the scheme it holds, which makes the name a reader
    states in a preference the same name they find on disk.
    """

    schemes: Dict[str, ShortcutScheme]

    @classmethod
    def load(cls, directory: Path) -> ShortcutCatalog:
        """Load every scheme the directory holds, ordered by name.

        Raises:
            SystemError: when the directory holds no scheme, or omits the default one.
            ValueError: when a scheme's name differs from its file stem.
        """
        schemes: Dict[str, ShortcutScheme] = {}
        for path in sorted(directory.glob(f"*{EXT_FILE_YAML}")):
            scheme = ShortcutScheme.load(path)
            if scheme.name != path.stem:
                raise ValueError(f"Keybinding file '{path}' holds scheme {scheme.name!r}; the two names must match")

            schemes[scheme.name] = scheme

        if not schemes:
            raise SystemError(f"Keybinding directory '{directory}' holds no scheme")

        if DEFAULT_SCHEME_NAME not in schemes:
            raise SystemError(
                f"Keybinding directory '{directory}' omits the default scheme {DEFAULT_SCHEME_NAME!r}. "
                f"Available schemes: {sorted(schemes)}"
            )

        return cls(schemes=dict(sorted(schemes.items())))

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(self.schemes)

    @property
    def default(self) -> ShortcutScheme:
        return self.schemes[DEFAULT_SCHEME_NAME]

    def get(self, name: str) -> ShortcutScheme:
        """The scheme of the given name.

        Raises:
            KeyError: when the catalog holds no scheme of that name.
        """
        if name not in self.schemes:
            raise KeyError(f"Unknown keybinding scheme {name!r}. Available schemes: {sorted(self.schemes)}")

        return self.schemes[name]

    def select(self, name: str) -> ShortcutScheme:
        """The scheme a stored preference names, falling back to the default.

        A preference outlives the build that wrote it, so a name a later build stopped
        shipping resolves to the default and the application keeps its keys.
        """
        if name not in self.schemes:
            logger.warning(f"Unknown keybinding scheme {name!r}, falling back to {DEFAULT_SCHEME_NAME!r}")
            return self.default

        return self.schemes[name]
