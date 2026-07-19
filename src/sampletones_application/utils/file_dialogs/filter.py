from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass(frozen=True)
class FileFilter:
    """
    An extension filter offered by a native file dialog.

    Carries a human-readable ``name`` and the ``*``-prefixed glob ``patterns`` it
    matches. Each backend renders these into its own filter syntax; ``label`` is the
    string a backend shows in the dialog's file-type selector.
    """

    name: str
    patterns: Tuple[str, ...]

    @property
    def label(self) -> str:
        """
        Returns the display string for the file-type selector.

        Combines the name and patterns as ``"name (pattern ...)"``. When the name is
        empty or already equals the joined patterns, the patterns stand alone so the
        label reads cleanly in either case.
        """
        joined = " ".join(self.patterns)
        if not self.name or self.name == joined:
            return joined

        return f"{self.name} ({joined})"


def normalize_extensions(extensions: Iterable[str]) -> Tuple[str, ...]:
    """
    Returns the extensions as ``*``-prefixed glob patterns.

    Accepts bare (``".stp"``) or already-globbed (``"*.stp"``) extensions and yields
    ``"*.stp"`` for each, so every backend receives a uniform pattern form.
    """
    return tuple(f"*{extension.removeprefix('*')}" for extension in extensions)
