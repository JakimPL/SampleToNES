from __future__ import annotations

from pathlib import Path
from typing import Final

from sampletones_application.ui.themes.dpg_constants import (
    CATEGORY_MAP,
    CORE_COLOR_MAP,
    CORE_STYLE_MAP,
    ITEM_TYPE_MAP,
    PLOTS_COLOR_MAP,
    PLOTS_STYLE_MAP,
)
from sampletones_application.ui.themes.items import ThemeItems
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
from sampletones_shared.utils.serialization import load_yaml

_MergeKey = tuple[int, bool, int, int]

_YAML_SUFFIX: Final[str] = ".yaml"


def _resolve_color_key(key: str, category: str) -> int:
    color_map = PLOTS_COLOR_MAP if category == "Plots" else CORE_COLOR_MAP
    if key not in color_map:
        raise ValueError(f"Unknown color key {key!r} for category {category!r}. " f"Valid keys: {sorted(color_map)}")
    return color_map[key]


def _resolve_style_key(key: str, category: str) -> int:
    style_map = PLOTS_STYLE_MAP if category == "Plots" else CORE_STYLE_MAP
    if key not in style_map:
        raise ValueError(f"Unknown style key {key!r} for category {category!r}. " f"Valid keys: {sorted(style_map)}")
    return style_map[key]


def _resolve_item_type(item_type: str) -> int:
    if item_type not in ITEM_TYPE_MAP:
        raise ValueError(f"Unknown item_type {item_type!r}. Valid types: {sorted(ITEM_TYPE_MAP)}")
    return ITEM_TYPE_MAP[item_type]


def _resolve_category(category: str) -> int:
    if category not in CATEGORY_MAP:
        raise ValueError(f"Unknown category {category!r}. Valid categories: {sorted(CATEGORY_MAP)}")
    return CATEGORY_MAP[category]


def _entry_to_runtime(entry: ThemeEntrySpec) -> ThemeValue:
    category_int = _resolve_category(entry.category)
    if isinstance(entry, ThemeColorEntrySpec):
        key_int = _resolve_color_key(entry.key, entry.category)
        return ThemeColor(key=key_int, color=entry.value, category=category_int)
    key_int = _resolve_style_key(entry.key, entry.category)
    return ThemeStyle(key=key_int, x=entry.x, y=entry.y, category=category_int)


def _merge_key(item_type_int: int, enabled: bool, entry: ThemeEntrySpec) -> _MergeKey:
    category_int = _resolve_category(entry.category)
    if isinstance(entry, ThemeColorEntrySpec):
        key_int = _resolve_color_key(entry.key, entry.category)
    else:
        key_int = _resolve_style_key(entry.key, entry.category)
    return (item_type_int, enabled, key_int, category_int)


def _spec_to_flat(spec: ThemeSpec) -> dict[_MergeKey, tuple[ThemeParameter, ThemeValue]]:
    flat: dict[_MergeKey, tuple[ThemeParameter, ThemeValue]] = {}
    for component in spec.components:
        item_type_int = _resolve_item_type(component.item_type)
        parameter = ThemeParameter(item_type=item_type_int, enabled_state=component.enabled)
        for entry in component.entries:
            key = _merge_key(item_type_int, component.enabled, entry)
            flat[key] = (parameter, _entry_to_runtime(entry))
    return flat


def _flat_to_items(
    flat: dict[_MergeKey, tuple[ThemeParameter, ThemeValue]],
) -> ThemeItems:
    grouped: dict[ThemeParameter, list[ThemeValue]] = {}
    for parameter, value in flat.values():
        grouped.setdefault(parameter, []).append(value)
    return ThemeItems(items=grouped)


class ThemeLoader:
    def __init__(self, theme_directory: Path) -> None:
        self._directory = theme_directory

    def load_all(self) -> list[Theme]:
        specs = self._load_specs()
        name_index = {spec.name: spec for spec in specs}
        self._check_for_cycles(name_index)
        ordered = self._topological_sort(specs, name_index)
        resolved_flats: dict[str, dict[_MergeKey, tuple[ThemeParameter, ThemeValue]]] = {}
        themes: list[Theme] = []
        for spec in ordered:
            flat = _spec_to_flat(spec)
            if spec.extends is not None:
                parent_flat = resolved_flats[spec.extends]
                merged = {**parent_flat, **flat}
            else:
                merged = flat
            resolved_flats[spec.name] = merged
            items = _flat_to_items(merged)
            themes.append(Theme(tag=spec.tag, items=items))
        return themes

    def _load_specs(self) -> list[ThemeSpec]:
        specs: list[ThemeSpec] = []
        for path in sorted(self._directory.rglob(f"*{_YAML_SUFFIX}")):
            raw = load_yaml(path)
            if not isinstance(raw, dict):
                raise TypeError(f"Theme file {path} must contain a mapping, got {type(raw)}")
            specs.append(ThemeSpec.model_validate(raw))
        return specs

    def _check_for_cycles(self, name_index: dict[str, ThemeSpec]) -> None:
        for name in name_index:
            visited: set[str] = set()
            current: str | None = name
            while current is not None:
                if current in visited:
                    raise ValueError(f"Cycle detected in theme inheritance: {name!r} → {current!r}")
                visited.add(current)
                spec = name_index.get(current)
                if spec is None:
                    raise ValueError(
                        f"Theme {name!r} extends unknown parent {current!r}. " f"Known themes: {sorted(name_index)}"
                    )
                current = spec.extends

    def _topological_sort(
        self,
        specs: list[ThemeSpec],
        name_index: dict[str, ThemeSpec],
    ) -> list[ThemeSpec]:
        ordered: list[ThemeSpec] = []
        visited: set[str] = set()

        def visit(spec: ThemeSpec) -> None:
            if spec.name in visited:
                return
            if spec.extends is not None:
                visit(name_index[spec.extends])
            visited.add(spec.name)
            ordered.append(spec)

        for spec in specs:
            visit(spec)
        return ordered
