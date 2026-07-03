from pathlib import Path
from typing import Dict, Final, List, Optional, Set

from sampletones_application.ui.themes.dpg_constants import (
    CATEGORY_MAP,
    CORE_COLOR_MAP,
    CORE_STYLE_MAP,
    ITEM_TYPE_MAP,
    PLOTS_COLOR_MAP,
    PLOTS_STYLE_MAP,
)
from sampletones_application.ui.themes.items import (
    ResolvedThemeEntry,
    ThemeEntries,
    ThemeEntryKey,
    ThemeItems,
)
from sampletones_application.ui.themes.spec import (
    ThemeColorEntrySpec,
    ThemeEntrySpec,
    ThemeSpec,
)
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
    ThemeValue,
)
from sampletones_application.ui.themes.theme import Theme
from sampletones_core.paths import EXT_FILE_YAML
from sampletones_shared.utils.serialization import load_yaml

_BASE_THEME_NAME: Final[str] = "default"


class ThemeLoader:
    """Resolves the theme YAML directory into complete runtime themes.

    Each spec composes on top of its parent (the base theme by default), and every
    enabled-state entry gains a disabled-state counterpart, so a loaded theme fully
    describes both item states and stays authoritative wherever it is bound.
    """

    def __init__(self, theme_directory: Path) -> None:
        self._directory = theme_directory

    def load_all(self) -> List[Theme]:
        specs = self._load_specs()
        name_index = {spec.name: spec for spec in specs}
        self._check_for_cycles(name_index)
        ordered = self._topological_sort(specs, name_index)

        resolved: Dict[str, ThemeEntries] = {}
        themes: List[Theme] = []
        for spec in ordered:
            entries = self._spec_to_entries(spec)
            parent = self._effective_parent(spec)
            merged = {**resolved[parent], **entries} if parent is not None else entries
            resolved[spec.name] = merged
            items = self._entries_to_items(self._mirror_disabled_entries(merged))
            themes.append(Theme(tag=spec.tag, items=items))

        return themes

    def _load_specs(self) -> List[ThemeSpec]:
        specs: List[ThemeSpec] = []
        for path in sorted(self._directory.rglob(f"*{EXT_FILE_YAML}")):
            raw = load_yaml(path)
            if not isinstance(raw, dict):
                raise TypeError(f"Theme file {path} must contain a mapping, got {type(raw)}")

            specs.append(ThemeSpec.model_validate(raw))

        return specs

    @staticmethod
    def _effective_parent(spec: ThemeSpec) -> Optional[str]:
        """The theme a spec composes on top of.

        A spec inherits from its explicit ``extends`` when given, and otherwise from
        the base theme, so every theme carries the shared base's complete component
        set and states only its own overrides. The base theme itself stands alone.
        This makes inheritance the default: a bound item theme always resolves to
        the global base plus its overrides, so every colour it omits keeps the
        base's value.
        """
        if spec.extends is not None:
            return spec.extends
        if spec.name != _BASE_THEME_NAME:
            return _BASE_THEME_NAME

        return None

    @staticmethod
    def _resolve_color_key(key: str, category: str) -> int:
        color_map = PLOTS_COLOR_MAP if category == "Plots" else CORE_COLOR_MAP
        if key not in color_map:
            raise ValueError(f"Unknown color key {key!r} for category {category!r}. Valid keys: {sorted(color_map)}")

        return color_map[key]

    @staticmethod
    def _resolve_style_key(key: str, category: str) -> int:
        style_map = PLOTS_STYLE_MAP if category == "Plots" else CORE_STYLE_MAP
        if key not in style_map:
            raise ValueError(f"Unknown style key {key!r} for category {category!r}. Valid keys: {sorted(style_map)}")

        return style_map[key]

    @staticmethod
    def _resolve_item_type(item_type: str) -> int:
        if item_type not in ITEM_TYPE_MAP:
            raise ValueError(f"Unknown item_type {item_type!r}. Valid types: {sorted(ITEM_TYPE_MAP)}")

        return ITEM_TYPE_MAP[item_type]

    @staticmethod
    def _resolve_category(category: str) -> int:
        if category not in CATEGORY_MAP:
            raise ValueError(f"Unknown category {category!r}. Valid categories: {sorted(CATEGORY_MAP)}")

        return CATEGORY_MAP[category]

    @classmethod
    def _entry_to_runtime(cls, entry: ThemeEntrySpec) -> ThemeValue:
        category = cls._resolve_category(entry.category)
        if isinstance(entry, ThemeColorEntrySpec):
            return ThemeColor(
                key=cls._resolve_color_key(entry.key, entry.category),
                color=entry.value,
                category=category,
            )

        return ThemeStyle(
            key=cls._resolve_style_key(entry.key, entry.category),
            x=entry.x,
            y=entry.y,
            category=category,
        )

    @classmethod
    def _entry_key(cls, item_type: int, enabled: bool, entry: ThemeEntrySpec) -> ThemeEntryKey:
        if isinstance(entry, ThemeColorEntrySpec):
            key = cls._resolve_color_key(entry.key, entry.category)
        else:
            key = cls._resolve_style_key(entry.key, entry.category)

        return ThemeEntryKey(
            item_type=item_type,
            enabled=enabled,
            key=key,
            category=cls._resolve_category(entry.category),
        )

    @classmethod
    def _spec_to_entries(cls, spec: ThemeSpec) -> ThemeEntries:
        entries: ThemeEntries = {}
        for component in spec.components:
            item_type = cls._resolve_item_type(component.item_type)
            parameter = ThemeParameter(
                item_type=item_type,
                enabled_state=component.enabled,
            )
            for entry in component.entries:
                entry_key = cls._entry_key(item_type, component.enabled, entry)
                entries[entry_key] = ResolvedThemeEntry(
                    parameter=parameter,
                    value=cls._entry_to_runtime(entry),
                )

        return entries

    @staticmethod
    def _mirror_disabled_entries(entries: ThemeEntries) -> ThemeEntries:
        """Gives every enabled-state entry an identical disabled-state counterpart.

        DearPyGui resolves each item against the theme component matching the
        item's enabled state, and it classifies many presentation items (menus,
        text labels, tree headers) as disabled; when the matching component is
        missing it re-applies its built-in palette, and the palette of the last
        themed item drawn bleeds into the global style, recolouring the entire
        application. Mirroring keeps every theme complete for both states, so items
        render with the theme's own values whichever state DearPyGui assigns them
        and the global style stays intact. Disabled-state entries stated explicitly
        in the YAML are preserved as written; that is where a visually muted
        disabled look belongs, scoped to the item types that need it (e.g. the base
        theme's disabled ``Button`` component).
        """
        mirrored = dict(entries)
        for entry_key, resolved_entry in entries.items():
            if not entry_key.enabled:
                continue

            target = ThemeEntryKey(
                item_type=entry_key.item_type,
                enabled=False,
                key=entry_key.key,
                category=entry_key.category,
            )
            if target in entries:
                continue

            mirrored[target] = ResolvedThemeEntry(
                parameter=ThemeParameter(
                    item_type=entry_key.item_type,
                    enabled_state=False,
                ),
                value=resolved_entry.value,
            )

        return mirrored

    @staticmethod
    def _entries_to_items(entries: ThemeEntries) -> ThemeItems:
        grouped: Dict[ThemeParameter, List[ThemeValue]] = {}
        for parameter, value in entries.values():
            grouped.setdefault(parameter, []).append(value)

        return ThemeItems(items=grouped)

    @classmethod
    def _check_for_cycles(cls, name_index: Dict[str, ThemeSpec]) -> None:
        for name in name_index:
            visited: Set[str] = set()
            current: Optional[str] = name
            while current is not None:
                if current in visited:
                    raise ValueError(f"Cycle detected in theme inheritance: {name!r} → {current!r}")

                visited.add(current)
                spec = name_index.get(current)
                if spec is None:
                    raise ValueError(
                        f"Theme {name!r} extends unknown parent {current!r}. Known themes: {sorted(name_index)}"
                    )

                current = cls._effective_parent(spec)

    @classmethod
    def _topological_sort(
        cls,
        specs: List[ThemeSpec],
        name_index: Dict[str, ThemeSpec],
    ) -> List[ThemeSpec]:
        ordered: List[ThemeSpec] = []
        visited: Set[str] = set()

        def visit(spec: ThemeSpec) -> None:
            if spec.name in visited:
                return

            parent = cls._effective_parent(spec)
            if parent is not None:
                visit(name_index[parent])

            visited.add(spec.name)
            ordered.append(spec)

        for spec in specs:
            visit(spec)

        return ordered
