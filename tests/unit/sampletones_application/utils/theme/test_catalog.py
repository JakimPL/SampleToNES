from pathlib import Path
from typing import Final

import pytest

from sampletones_application.utils.palette.palette import Palette
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.utils.theme.catalog import ThemeEntryAddress, ThemeSpecCatalog
from sampletones_application.utils.theme.spec import BASE_THEME_NAME, CORE_CATEGORY, EVERY_ITEM_TYPE_NAME

_BASE: Final[str] = """
name: default
tag: synthetic.default
components:
  - item_type: All
    entries:
      - type: color
        key: Text
        value: .ink
      - type: color
        key: Border
        value: "#101010"
      - type: style
        key: ChildRounding
        x: 8
  - item_type: Button
    entries:
      - type: color
        key: Button
        value: .ink
  - item_type: Button
    enabled: false
    entries:
      - type: color
        key: Button
        value: "#2e2e3c"
"""
_PANEL: Final[str] = """
name: panel
tag: synthetic.panel
components:
  - item_type: All
    entries:
      - type: color
        key: Text
        value: .paper
"""
_INNER: Final[str] = """
name: inner
tag: synthetic.inner
extends: panel
components:
  - item_type: All
    entries:
      - type: color
        key: ChildBg
        value: .paper
"""
_PALETTE: Final[str] = """
name: synthetic
colors:
  ink: "#e0e0e0"
  paper: "#202020"
"""


def _address(key: str, *, item_type: str, enabled: bool) -> ThemeEntryAddress:
    return ThemeEntryAddress(item_type=item_type, enabled=enabled, category=CORE_CATEGORY, key=key)


@pytest.fixture
def source(tmp_path: Path) -> PaletteSource:
    palette_file = tmp_path / "synthetic.yaml"
    palette_file.write_text(_PALETTE)
    return PaletteSource(Palette.load(palette_file))


@pytest.fixture
def catalog(tmp_path: Path, source: PaletteSource) -> ThemeSpecCatalog:
    themes = tmp_path / "themes"
    themes.mkdir()
    (themes / "default.yaml").write_text(_BASE)
    (themes / "panel.yaml").write_text(_PANEL)
    (themes / "inner.yaml").write_text(_INNER)
    return ThemeSpecCatalog.load(themes, source)


class TestComposition:
    def test_parents_come_before_the_themes_built_on_them(self, catalog: ThemeSpecCatalog) -> None:
        names = [spec.name for spec in catalog.ordered]

        assert names.index(BASE_THEME_NAME) < names.index("panel") < names.index("inner")

    def test_a_theme_keeps_its_own_override(self, catalog: ThemeSpecCatalog, source: PaletteSource) -> None:
        color = catalog.color("panel", _address("Text", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))

        assert color.rgba == source.palette.colors["paper"]

    def test_a_theme_inherits_what_its_parents_state(self, catalog: ThemeSpecCatalog) -> None:
        inherited = catalog.color("inner", _address("Border", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))
        base = catalog.color(BASE_THEME_NAME, _address("Border", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))

        assert inherited.rgba == base.rgba


class TestLookup:
    def test_an_item_type_reads_the_every_type_component_where_its_own_states_nothing(
        self,
        catalog: ThemeSpecCatalog,
    ) -> None:
        button_text = catalog.color(BASE_THEME_NAME, _address("Text", item_type="Button", enabled=True))
        every_text = catalog.color(BASE_THEME_NAME, _address("Text", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))

        assert button_text.rgba == every_text.rgba

    def test_the_disabled_state_reads_the_enabled_entry_where_it_states_none(
        self,
        catalog: ThemeSpecCatalog,
    ) -> None:
        disabled = catalog.color(BASE_THEME_NAME, _address("Text", item_type=EVERY_ITEM_TYPE_NAME, enabled=False))
        enabled = catalog.color(BASE_THEME_NAME, _address("Text", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))

        assert disabled.rgba == enabled.rgba

    def test_an_explicit_disabled_entry_wins(self, catalog: ThemeSpecCatalog) -> None:
        disabled = catalog.color(BASE_THEME_NAME, _address("Button", item_type="Button", enabled=False))
        enabled = catalog.color(BASE_THEME_NAME, _address("Button", item_type="Button", enabled=True))

        assert disabled.rgba != enabled.rgba

    def test_a_style_answers_with_its_components(self, catalog: ThemeSpecCatalog) -> None:
        assert catalog.style(BASE_THEME_NAME, _address("ChildRounding", item_type="Button", enabled=True)) == (
            8.0,
            -1.0,
        )

    def test_an_entry_no_component_states_is_refused(self, catalog: ThemeSpecCatalog) -> None:
        with pytest.raises(KeyError):
            catalog.color(BASE_THEME_NAME, _address("WindowBg", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))

    def test_a_style_read_as_a_color_is_refused(self, catalog: ThemeSpecCatalog) -> None:
        with pytest.raises(KeyError):
            catalog.color(BASE_THEME_NAME, _address("ChildRounding", item_type=EVERY_ITEM_TYPE_NAME, enabled=True))


class TestInheritanceErrors:
    def test_an_unknown_parent_is_refused(self, tmp_path: Path, source: PaletteSource) -> None:
        (tmp_path / "default.yaml").write_text(_BASE)
        (tmp_path / "inner.yaml").write_text(_INNER)

        with pytest.raises(ValueError):
            ThemeSpecCatalog.load(tmp_path, source)

    def test_a_cycle_is_refused(self, tmp_path: Path, source: PaletteSource) -> None:
        (tmp_path / "default.yaml").write_text(_BASE)
        (tmp_path / "panel.yaml").write_text(
            _PANEL.replace("tag: synthetic.panel", "tag: synthetic.panel\nextends: inner")
        )
        (tmp_path / "inner.yaml").write_text(_INNER)

        with pytest.raises(ValueError):
            ThemeSpecCatalog.load(tmp_path, source)
