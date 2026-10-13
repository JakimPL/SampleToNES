from pathlib import Path
from typing import Dict, List

from sampletones_application.ui.themes.dpg_constants import (
    CATEGORY_MAP,
    CORE_COLOR_MAP,
    CORE_STYLE_MAP,
    EVERY_ITEM_TYPE,
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
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
    ThemeValue,
)
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.utils.theme.catalog import ThemeSpecCatalog
from sampletones_application.utils.theme.spec import (
    ThemeColorEntrySpec,
    ThemeEntrySpec,
    ThemeSpec,
)


class ThemeLoader:
    """Resolves the theme YAML directory into complete runtime themes.

    The specs come from :class:`ThemeSpecCatalog`, parents first. Each spec composes on top of
    its parent (the base theme by default), and every enabled-state entry gains a disabled-state
    counterpart, so a loaded theme fully describes both item states and stays authoritative
    wherever it is bound.
    """

    def __init__(self, theme_directory: Path, palette_source: PaletteSource) -> None:
        self._directory = theme_directory
        self._palette_source = palette_source

    def load_all(self) -> List[Theme]:
        catalog = ThemeSpecCatalog.load(self._directory, self._palette_source)
        resolved: Dict[str, ThemeEntries] = {}
        themes: List[Theme] = []
        for spec in catalog.ordered:
            entries = self._spec_to_entries(spec)
            parent = spec.parent
            merged = {**resolved[parent], **entries} if parent is not None else entries
            resolved[spec.name] = merged
            items = self._entries_to_items(self._mirror_disabled_entries(merged))
            themes.append(Theme(tag=spec.tag, items=items))

        return themes

    @staticmethod
    def _resolve_color_key(key: str, category: str) -> int:
        color_map = PLOTS_COLOR_MAP if category == "Plots" else CORE_COLOR_MAP
        if key not in color_map:
            raise KeyError(f"Unknown color key {key!r} for category {category!r}. Valid keys: {sorted(color_map)}")

        return color_map[key]

    @staticmethod
    def _resolve_style_key(key: str, category: str) -> int:
        style_map = PLOTS_STYLE_MAP if category == "Plots" else CORE_STYLE_MAP
        if key not in style_map:
            raise KeyError(f"Unknown style key {key!r} for category {category!r}. Valid keys: {sorted(style_map)}")

        return style_map[key]

    @staticmethod
    def _resolve_item_type(item_type: str) -> int:
        if item_type not in ITEM_TYPE_MAP:
            raise KeyError(f"Unknown item_type {item_type!r}. Valid types: {sorted(ITEM_TYPE_MAP)}")

        return ITEM_TYPE_MAP[item_type]

    @staticmethod
    def _resolve_category(category: str) -> int:
        if category not in CATEGORY_MAP:
            raise KeyError(f"Unknown category {category!r}. Valid categories: {sorted(CATEGORY_MAP)}")

        return CATEGORY_MAP[category]

    def _entry_to_runtime(self, entry: ThemeEntrySpec) -> ThemeValue:
        category = self._resolve_category(entry.category)
        if isinstance(entry, ThemeColorEntrySpec):
            return ThemeColor(
                key=self._resolve_color_key(entry.key, entry.category),
                color=entry.value,
                category=category,
            )

        return ThemeStyle(
            key=self._resolve_style_key(entry.key, entry.category),
            x=entry.x,
            y=entry.y,
            category=category,
        )

    @classmethod
    def _entry_key(
        cls,
        item_type: int,
        enabled: bool,
        entry: ThemeEntrySpec,
    ) -> ThemeEntryKey:
        is_style = not isinstance(entry, ThemeColorEntrySpec)
        if isinstance(entry, ThemeColorEntrySpec):
            key = cls._resolve_color_key(entry.key, entry.category)
        else:
            key = cls._resolve_style_key(entry.key, entry.category)

        return ThemeEntryKey(
            item_type=item_type,
            enabled=enabled,
            key=key,
            category=cls._resolve_category(entry.category),
            is_style=is_style,
        )

    def _spec_to_entries(self, spec: ThemeSpec) -> ThemeEntries:
        entries: ThemeEntries = {}
        for component in spec.components:
            item_type = self._resolve_item_type(component.item_type)
            parameter = ThemeParameter(
                item_type=item_type,
                enabled_state=component.enabled,
            )
            for entry in component.entries:
                entry_key = self._entry_key(item_type, component.enabled, entry)
                entries[entry_key] = ResolvedThemeEntry(
                    parameter=parameter,
                    value=self._entry_to_runtime(entry),
                )

        return entries

    @staticmethod
    def _mirror_disabled_entries(entries: ThemeEntries) -> ThemeEntries:
        """Gives every enabled-state entry an identical disabled-state counterpart.

        DearPyGui resolves each item against the theme component matching the
        item's enabled state, and it classifies many presentation items (menus,
        text labels, tree headers) as disabled; when the matching component is
        missing it re-applies its built-in palette, and the palette of the last
        themed item drawn bleeds into the global style, recoloring the entire
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
                is_style=entry_key.is_style,
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
        """Gathers the entries into the components a theme is built from, broadest first.

        DearPyGui fills an item's colors by walking a theme's components in the order they were
        created, so the last one covering a color is the one the item wears. A component naming a
        single item type states what that type is meant to look like, and one naming every type
        states the ground it stands on, so the ground is laid first and the item type paints over
        it. Ordering them here keeps that true whichever order a theme and the theme it extends
        happened to state them in, and whichever entries the disabled-state mirror added.
        """
        grouped: Dict[ThemeParameter, List[ThemeValue]] = {}
        for parameter, value in entries.values():
            grouped.setdefault(parameter, []).append(value)

        ordered = sorted(grouped, key=lambda parameter: parameter.item_type != EVERY_ITEM_TYPE)
        return ThemeItems(items={parameter: grouped[parameter] for parameter in ordered})
