from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class FileFilter:
    """
    One file type offered by a native file dialog.

    Carries a human-readable ``name`` and the ``*``-prefixed glob ``patterns`` it
    matches. Each backend renders these into its own filter syntax; ``label`` is the
    string a backend shows in the dialog's file-type selector.
    """

    name: str
    patterns: Tuple[str, ...]

    @classmethod
    def for_extensions(
        cls,
        name: str,
        extensions: Iterable[str],
    ) -> FileFilter:
        """
        Returns the type matching ``extensions``, shown under ``name``.

        Accepts bare or already-globbed extensions, so a caller names the extensions it
        writes and the glob form stays an implementation detail of the dialog layer.

        Args:
            name: The human-readable name the dialog shows this type under.
            extensions: The extensions the type matches, leading dot included.

        Returns:
            FileFilter: The type a dialog offers for those extensions.
        """
        return cls(name=name, patterns=normalize_extensions(extensions))

    @property
    def extensions(self) -> Tuple[str, ...]:
        """The extensions this type matches, leading dot included."""
        return tuple(pattern.removeprefix("*") for pattern in self.patterns)

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


def merge_filters(filters: Tuple[FileFilter, ...]) -> Optional[FileFilter]:
    """
    Returns the one type a dialog limited to a single filter offers.

    A dialog that takes one filter still accepts every type: the names join into one label
    and the patterns gather behind it, so each accepted extension is named on screen and
    every matching file stays reachable in the browser. One type passes through as it is,
    which is the form that lets a dialog fill its extension in on its own.

    Args:
        filters: The types the dialog was asked to offer.

    Returns:
        Optional[FileFilter]: The single type to offer, or ``None`` when none was asked for.
    """
    if not filters:
        return None

    if len(filters) == 1:
        return filters[0]

    names = ", ".join(file_filter.name for file_filter in filters if file_filter.name)
    patterns = chain.from_iterable(file_filter.patterns for file_filter in filters)
    return FileFilter(name=names, patterns=tuple(dict.fromkeys(patterns)))
