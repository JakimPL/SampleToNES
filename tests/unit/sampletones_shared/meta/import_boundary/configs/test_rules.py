from collections import Counter
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest
from pydantic import ValidationError

from sampletones_shared.meta.import_boundary.check import check_boundaries
from sampletones_shared.meta.import_boundary.configs.declaration import BoundaryDeclaration
from sampletones_shared.meta.import_boundary.configs.general import GeneralBoundaries
from sampletones_shared.meta.import_boundary.configs.rules import ImportBoundaryRules
from sampletones_shared.meta.import_boundary.graph import reached_units
from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from sampletones_shared.meta.import_boundary.scope import rule_modules
from sampletones_shared.paths.source import SOURCE_ROOT
from tests.suite.source import swept_paths, write_module

BOUNDARIES: Final[ImportBoundaryRules] = ImportBoundaryRules.load()

APPLICATION: Final[str] = "sampletones_application"
CORE: Final[str] = "sampletones_core"
PLAYER: Final[str] = "sampletones_player"
ASSEMBLER: Final[str] = "sampletones_player.driver.assembler"

VISUAL_IMPORT: Final[str] = "import dearpygui.dearpygui as dpg\n"
CONTRACT_IMPORT: Final[str] = "from sampletones_application.services.result import ServiceResult\n"
PLAIN_IMPORT: Final[str] = "from sampletones_core.project.project import Project\n"
PLAYER_IMPORT: Final[str] = "from sampletones_player.song import Song\n"
ASSEMBLER_IMPORT: Final[str] = "from sampletones_player.driver.assembler.builder import build_driver\n"
DRIVER_IMPORT: Final[str] = "from sampletones_player.driver.image import DriverImage\n"
PANEL_SUFFIX: Final[str] = "def build() -> None:\n    dpg.add_group(parent=SUF_PANEL_LEFT)\n"


def reached_modules(rule: BoundaryRule) -> List[Path]:
    """The modules a rule of the real source tree applies to."""
    root = SOURCE_ROOT / rule.root
    return rule_modules(root, rule.pattern, rule.excluding, swept_paths(root), None)


def reported(tmp_path: Path) -> List[str]:
    """What the shipped declaration reports over a tree a test builds."""
    violations = check_boundaries(
        tmp_path,
        BOUNDARIES.boundary_rules(),
        BOUNDARIES.tokens,
        None,
    )
    return [violation.kind for violation in violations]


class TestPackageGraph:
    """The packages under the source root, and the order they may reach each other in."""

    LAYERS: Final[Dict[str, Tuple[str, ...]]] = BOUNDARIES.graphs["packages"].layers

    def test_every_package_of_the_source_tree_is_declared(self) -> None:
        directories = {path.name for path in SOURCE_ROOT.iterdir() if (path / "__init__.py").is_file()}

        assert set(self.LAYERS) == directories

    def test_the_reconstruction_engine_stays_clear_of_the_console_player(self) -> None:
        assert PLAYER not in reached_units(self.LAYERS, CORE)

    def test_the_console_player_reads_the_reconstruction_engine(self) -> None:
        assert CORE in self.LAYERS[PLAYER]

    def test_the_synthesis_package_stands_below_the_reconstruction_engine(self) -> None:
        """Equal temperament sits in `sampletones_shared`, so synthesis reaches no engine module."""
        assert CORE not in reached_units(self.LAYERS, "sampletones_synthesis")


class TestPlayerGraph:
    """The player's own subpackages, and the order they may reach each other in."""

    LAYERS: Final[Dict[str, Tuple[str, ...]]] = BOUNDARIES.graphs["player"].layers

    def test_the_specification_is_the_layer_everything_stands_on(self) -> None:
        assert self.LAYERS["specification"] == ()

    def test_the_build_toolchain_is_reached_from_no_shipped_module(self) -> None:
        """`driver/assembler/` stays outside the wheel, so an import of it breaks an installed copy."""
        assert all("driver/assembler" not in layers for layers in self.LAYERS.values())

    def test_the_driver_is_reached_through_the_file_that_writes_the_nsf(self) -> None:
        assert "driver" in self.LAYERS["nsf"]

    def test_every_module_of_the_player_belongs_to_one_unit(self) -> None:
        rules = BOUNDARIES.graphs["player"].rules()
        owners = Counter(path for rule in rules for path in reached_modules(rule))

        assert set(owners) == swept_paths(SOURCE_ROOT / PLAYER)
        assert set(owners.values()) == {1}


class TestNamedGroups:
    """A declaration names the groups it draws on, so a name reaching none is refused as it is read."""

    def test_a_declaration_naming_no_declared_group_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            ImportBoundaryRules(
                general=GeneralBoundaries(groups={}),
                graphs={},
                rules=(
                    BoundaryDeclaration(
                        root=APPLICATION,
                        pattern="logic/**/*.py",
                        forbidden_groups=("absent",),
                    ),
                ),
                tokens=(),
            )


class TestDeclaredRules:
    """Each declared boundary read over a tree that crosses it."""

    def test_a_layer_reaching_the_interface_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / APPLICATION / "logic", "direct.py", VISUAL_IMPORT)

        assert reported(tmp_path) == ["dearpygui"]

    def test_a_service_contract_stays_reachable(self, tmp_path: Path) -> None:
        """A layer reads another layer's data contract while its implementation stays out of reach."""
        write_module(tmp_path / APPLICATION / "logic", "direct.py", CONTRACT_IMPORT)

        assert reported(tmp_path) == []

    def test_the_reconstruction_engine_reaching_the_console_player_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / CORE / "formats", "player.py", PLAYER_IMPORT)

        assert reported(tmp_path) == [PLAYER]

    def test_the_console_player_reading_the_engine_is_left_alone(self, tmp_path: Path) -> None:
        write_module(tmp_path / PLAYER / "nsf", "file.py", PLAIN_IMPORT)

        assert reported(tmp_path) == []

    def test_a_shipped_module_reaching_the_build_toolchain_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / PLAYER / "nsf", "file.py", ASSEMBLER_IMPORT)

        assert reported(tmp_path) == [ASSEMBLER]

    def test_the_build_toolchain_reads_the_driver_it_assembles(self, tmp_path: Path) -> None:
        write_module(tmp_path / PLAYER / "driver" / "assembler", "builder.py", DRIVER_IMPORT)

        assert reported(tmp_path) == []

    def test_a_panel_composing_a_column_suffix_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / APPLICATION / "ui" / "panels", "left.py", PANEL_SUFFIX)

        assert len(reported(tmp_path)) == 1


class TestRuleCoverage:
    """A rule naming no module of the tree reads as a clean tree, so each one reaches something."""

    def test_the_source_root_holds_modules(self) -> None:
        assert swept_paths(SOURCE_ROOT)

    def test_every_boundary_rule_reaches_a_module(self) -> None:
        assert all(reached_modules(rule) for rule in BOUNDARIES.boundary_rules())

    def test_every_token_rule_reaches_a_module(self) -> None:
        assert all(list((SOURCE_ROOT / rule.root).glob(rule.pattern)) for rule in BOUNDARIES.tokens)
