from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.written import PALETTE_SOURCE_CONTEXT_KEY
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.utils.theme.spec import (
    EVERY_ITEM_TYPE_NAME,
    ThemeColorEntrySpec,
    ThemeEntrySpec,
    ThemeSpec,
    ThemeStyleEntrySpec,
)
from sampletones_shared.paths.extensions import EXT_FILE_YAML
from sampletones_shared.utils.serialization import load_yaml


@dataclass(frozen=True)
class ThemeEntryAddress:
    """Where one entry of a theme sits: the item type it styles, the state it applies in, its
    category and its key, all as the theme files spell them."""

    item_type: str
    enabled: bool
    category: str
    key: str


ThemeEntries = Dict[ThemeEntryAddress, ThemeEntrySpec]


class ThemeSpecCatalog:
    """Every theme the configuration states, each with the entries it wears once composed.

    A theme composes on top of its parent (:attr:`ThemeSpec.parent`), so a theme's entries are
    its parent's with its own laid over them, and the specs are kept parents first. A lookup
    answers what an item of a given type and state draws with: the entry its own component
    states, the enabled state's entry where the disabled state states none, and the component
    naming every item type where the item's own type states nothing. That is how DearPyGui
    resolves a bound theme, so a reader of this catalog sees the value the application draws.
    """

    def __init__(self, specs: List[ThemeSpec]) -> None:
        self._index = {spec.name: spec for spec in specs}
        self._check_parents()
        self._ordered = self._parents_first(specs)
        self._entries = self._compose()

    @classmethod
    def load(
        cls,
        directory: Path,
        palette_source: PaletteSource,
    ) -> ThemeSpecCatalog:
        """Every theme file under ``directory``, its colors bound to ``palette_source``.

        Raises:
            TypeError: If a theme file holds something other than a mapping.
            ValueError: If a theme extends an unknown theme or the inheritance forms a cycle.
        """
        context = {PALETTE_SOURCE_CONTEXT_KEY: palette_source}
        specs: List[ThemeSpec] = []
        for path in sorted(directory.rglob(f"*{EXT_FILE_YAML}")):
            raw = load_yaml(path)
            if not isinstance(raw, dict):
                raise TypeError(f"Theme file {path} must contain a mapping, got {type(raw)}")

            specs.append(ThemeSpec.model_validate(raw, context=context))

        return cls(specs)

    @property
    def ordered(self) -> List[ThemeSpec]:
        """Every theme, each after the theme it composes on."""
        return list(self._ordered)

    def entries(self, name: str) -> ThemeEntries:
        """The entries theme ``name`` wears: its parent's, with its own laid over them.

        Raises:
            KeyError: If no theme carries that name.
        """
        return dict(self._entries[name])

    def color(
        self,
        name: str,
        address: ThemeEntryAddress,
    ) -> BaseColor:
        """The color theme ``name`` gives the entry at ``address``.

        Raises:
            KeyError: If the theme states no color there, for that item type or every item type.
        """
        entry = self._resolve(name, address)
        if not isinstance(entry, ThemeColorEntrySpec):
            raise KeyError(f"Theme {name!r} states a style, not a color, at {address}")

        return entry.value

    def style(
        self,
        name: str,
        address: ThemeEntryAddress,
    ) -> Tuple[float, float]:
        """The style value theme ``name`` gives the entry at ``address``, as its two components.

        Raises:
            KeyError: If the theme states no style there, for that item type or every item type.
        """
        entry = self._resolve(name, address)
        if not isinstance(entry, ThemeStyleEntrySpec):
            raise KeyError(f"Theme {name!r} states a color, not a style, at {address}")

        return entry.x, entry.y

    def _resolve(
        self,
        name: str,
        address: ThemeEntryAddress,
    ) -> ThemeEntrySpec:
        entries = self._entries[name]
        for candidate in self._candidates(address):
            if candidate in entries:
                return entries[candidate]

        raise KeyError(f"Theme {name!r} states nothing at {address}")

    @staticmethod
    def _candidates(address: ThemeEntryAddress) -> Iterator[ThemeEntryAddress]:
        for item_type in dict.fromkeys((address.item_type, EVERY_ITEM_TYPE_NAME)):
            yield replace(address, item_type=item_type)
            if not address.enabled:
                yield replace(address, item_type=item_type, enabled=True)

    def _compose(self) -> Dict[str, ThemeEntries]:
        composed: Dict[str, ThemeEntries] = {}
        for spec in self._ordered:
            own = self._own_entries(spec)
            parent = spec.parent
            composed[spec.name] = {**composed[parent], **own} if parent is not None else own

        return composed

    @staticmethod
    def _own_entries(spec: ThemeSpec) -> ThemeEntries:
        entries: ThemeEntries = {}
        for component in spec.components:
            for entry in component.entries:
                address = ThemeEntryAddress(
                    item_type=component.item_type,
                    enabled=component.enabled,
                    category=entry.category,
                    key=entry.key,
                )
                entries[address] = entry

        return entries

    def _check_parents(self) -> None:
        for name in self._index:
            visited: Set[str] = set()
            current: Optional[str] = name
            while current is not None:
                if current in visited:
                    raise ValueError(f"Cycle detected in theme inheritance: {name!r} → {current!r}")

                visited.add(current)
                spec = self._index.get(current)
                if spec is None:
                    raise ValueError(
                        f"Theme {name!r} extends unknown parent {current!r}. Known themes: {sorted(self._index)}"
                    )

                current = spec.parent

    def _parents_first(self, specs: List[ThemeSpec]) -> List[ThemeSpec]:
        ordered: List[ThemeSpec] = []
        visited: Set[str] = set()

        def visit(spec: ThemeSpec) -> None:
            if spec.name in visited:
                return

            parent = spec.parent
            if parent is not None:
                visit(self._index[parent])

            visited.add(spec.name)
            ordered.append(spec)

        for spec in specs:
            visit(spec)

        return ordered
