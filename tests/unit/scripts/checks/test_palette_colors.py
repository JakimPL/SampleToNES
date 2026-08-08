from pathlib import Path
from typing import Final, List, Tuple

from pytest import fixture

from sampletones_shared.meta.source.modules import SourceModule
from scripts.checks.palette_colors import dpg_module_helper
from tests.suite.scripts import load_script
from tests.suite.source import parse_source

check_palette_colors = load_script("checks/palette_colors.py")

PANEL_MODULE: Final[Path] = Path("ui/panel.py")

PANEL_SOURCE: Final[str] = """
class GUIPanel:
    def __init__(self, layout) -> None:
        self._tint = layout.colors.accent.rgba
        self._colors = layout.colors
        cls._border: ColorRGBA = layout.colors.border.rgba
        self._theme = create_theme(layout.colors.text.rgba)
        local = layout.colors.text.rgba

    def draw(self) -> None:
        dpg.add_text("value", color=self._colors.accent.rgba)
"""

PALETTE_FILE: Final[str] = 'colors:\n  accent: "#a97fe3"\n'
LAYOUT_FILE: Final[str] = 'label_color: .accent\nclip_color: "#ff5555"\n'


@fixture
def module_helpers() -> Tuple[Path, str]:
    return dpg_module_helper()


def messages(source: str) -> List[str]:
    module = SourceModule(path=PANEL_MODULE, tree=parse_source(source))
    return [finding.message for finding in check_palette_colors.stored_colors(module)]


def locations(source: str) -> List[str]:
    module = SourceModule(path=PANEL_MODULE, tree=parse_source(source))
    return [finding.location for finding in check_palette_colors.stored_colors(module)]


def theme_color_messages(
    source: str,
    module_helpers: Tuple[Path, str],
    path: Path = PANEL_MODULE,
) -> List[str]:
    bindings_module, theme_color_helper = module_helpers
    module = SourceModule(path=path, tree=parse_source(source))
    return [
        finding.message
        for finding in check_palette_colors.unregistered_theme_colors(
            module,
            bindings_module=bindings_module,
            theme_color_helper=theme_color_helper,
        )
    ]


class TestStoredColors:
    def test_an_attribute_assigned_the_resolved_value_is_reported(self) -> None:
        assert len(messages(PANEL_SOURCE)) == 2

    def test_the_report_names_the_assignment_line(self) -> None:
        assert locations(PANEL_SOURCE) == [f"{PANEL_MODULE}:4", f"{PANEL_MODULE}:6"]

    def test_an_attribute_holding_the_palette_colour_passes(self) -> None:
        source = "class GUIPanel:\n    def __init__(self, layout) -> None:\n        self._c = layout.colors\n"

        assert not messages(source)

    def test_a_resolved_value_handed_straight_to_dearpygui_passes(self) -> None:
        assert not messages('def draw(self) -> None:\n    dpg.add_text("v", color=self._colors.accent.rgba)\n')

    def test_a_resolved_value_reaching_a_call_passes(self) -> None:
        assert not messages("class P:\n    def f(self, layout) -> None:\n        self._t = build(layout.c.text.rgba)\n")

    def test_a_local_holding_the_resolved_value_passes(self) -> None:
        assert not messages("def f(layout) -> None:\n    local = layout.colors.text.rgba\n")


class TestUnregisteredThemeColors:
    def test_a_theme_colour_filled_directly_is_reported(
        self,
        module_helpers: Tuple[Path, str],
    ) -> None:
        source = "def build() -> None:\n    dpg.add_theme_color(dpg.mvThemeCol_Text, color.rgba)\n"

        assert len(theme_color_messages(source, module_helpers)) == 1

    def test_the_helper_that_records_it_passes(
        self,
        module_helpers: Tuple[Path, str],
    ) -> None:
        source = "def build() -> None:\n    dpg_add_palette_theme_color(dpg.mvThemeCol_Text, color)\n"

        assert not theme_color_messages(source, module_helpers)

    def test_a_theme_style_passes(
        self,
        module_helpers: Tuple[Path, str],
    ) -> None:
        source = "def build() -> None:\n    dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)\n"

        assert not theme_color_messages(source, module_helpers)


class TestLiteralColors:
    def test_a_hex_colour_outside_the_palettes_is_reported(self, tmp_path: Path) -> None:
        (tmp_path / "settings.yaml").write_text(LAYOUT_FILE)

        findings = check_palette_colors.find_literal_colors(tmp_path, tmp_path / "palettes")

        assert [finding.location for finding in findings] == [f"{tmp_path / 'settings.yaml'}:2"]

    def test_a_palette_carries_its_colours_as_values(self, tmp_path: Path) -> None:
        palettes = tmp_path / "palettes"
        palettes.mkdir()
        (palettes / "studio.yaml").write_text(PALETTE_FILE)

        assert check_palette_colors.find_literal_colors(tmp_path, palettes) == []

    def test_a_token_reference_passes(self, tmp_path: Path) -> None:
        (tmp_path / "settings.yaml").write_text("label_color: .accent\n")

        assert check_palette_colors.find_literal_colors(tmp_path, tmp_path / "palettes") == []
