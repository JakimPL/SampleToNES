from collections import Counter
from pathlib import Path
from typing import Dict, Final, List, Set, Tuple

import pytest

from sampletones_shared.meta.source.modules import source_paths
from sampletones_shared.paths.source import SOURCE_ROOT
from tests.suite.scripts import load_script

check_import_boundary = load_script("checks/import_boundary.py")

APPLICATION: Final[str] = "sampletones_application"
PLAYER: Final[str] = "sampletones_player"
LOGIC_RULE: Final[str] = "logic/**/*.py"

FORBIDDEN_IMPORT: Final[str] = "import dearpygui.dearpygui as dpg\n"
CONTRACT_IMPORT: Final[str] = "from sampletones_application.services.result import ServiceResult\n"
PLAIN_IMPORT: Final[str] = "from sampletones_core.project.project import Project\n"
PLAYER_IMPORT: Final[str] = "from sampletones_player.song import Song\n"
ASSEMBLER_IMPORT: Final[str] = "from sampletones_player.driver.assembler.builder import build_driver\n"
PANEL_SUFFIX: Final[str] = "def build() -> None:\n    dpg.add_group(parent=SUF_PANEL_LEFT)\n"


def write_module(directory: Path, name: str, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def swept(package: Path) -> List[Path]:
    return [path.resolve() for path in source_paths([package])]


def reached_modules(rule: check_import_boundary.BoundaryRule) -> List[Path]:
    """The modules a rule of the real source tree applies to."""
    root = SOURCE_ROOT / rule.root
    return check_import_boundary.rule_modules(
        root,
        rule.pattern,
        rule.excluding,
        {path.resolve() for path in source_paths([root])},
        None,
    )


def reaches(layers: Dict[str, Tuple[str, ...]], unit: str, seen: Set[str]) -> Set[str]:
    """Every unit a unit imports, directly or through the units it imports."""
    for allowed in layers[unit]:
        if allowed not in seen:
            seen.add(allowed)
            reaches(layers, allowed, seen)

    return seen


class TestUnitGlobs:
    """A unit names either one module or a directory of them, and reads as both."""

    def test_a_directory_unit_reaches_every_module_below_it(self) -> None:
        assert check_import_boundary.unit_glob("driver") == "driver/**/*.py"

    def test_a_module_unit_names_itself(self) -> None:
        assert check_import_boundary.unit_glob("song.py") == "song.py"

    def test_a_unit_under_a_package_is_reached_by_a_dotted_prefix(self) -> None:
        assert check_import_boundary.unit_prefix(PLAYER, "driver/assembler") == "sampletones_player.driver.assembler"

    def test_a_module_unit_drops_its_suffix(self) -> None:
        assert check_import_boundary.unit_prefix(PLAYER, "song.py") == "sampletones_player.song"

    def test_a_package_unit_is_reached_by_its_own_name(self) -> None:
        assert check_import_boundary.unit_prefix("", "sampletones_core") == "sampletones_core"

    def test_a_nested_unit_is_named_as_the_glob_it_owns(self) -> None:
        nested = check_import_boundary.nested_globs("driver", ("driver", "driver/assembler", "clock"))
        assert nested == ("driver/assembler/**/*.py",)


class TestLayerRules:
    """A graph states what a unit may import, and the rule the check runs is what remains."""

    GRAPH: Final = check_import_boundary.LayerGraph(
        root="package",
        package="package",
        layers={"low": (), "high": ("low",)},
        contracts={"low": ("package.high.contract",)},
    )

    def test_a_unit_forbids_the_units_its_layers_leave_out(self) -> None:
        low, _ = check_import_boundary.layer_rules(self.GRAPH)
        assert low.forbidden == ("package.high",)

    def test_a_unit_stays_free_of_the_units_it_may_import(self) -> None:
        _, high = check_import_boundary.layer_rules(self.GRAPH)
        assert high.forbidden == ()

    def test_a_unit_carries_the_contracts_declared_for_it(self) -> None:
        low, _ = check_import_boundary.layer_rules(self.GRAPH)
        assert low.contracts == ("package.high.contract",)

    def test_every_rule_is_written_against_the_graphs_root(self) -> None:
        assert all(rule.root == "package" for rule in check_import_boundary.layer_rules(self.GRAPH))


class TestPackageGraph:
    """The packages under the source root, and the order they may reach each other in."""

    LAYERS: Final[Dict[str, Tuple[str, ...]]] = check_import_boundary.PACKAGE_LAYERS

    def test_every_package_of_the_source_tree_is_declared(self) -> None:
        directories = {path.name for path in SOURCE_ROOT.iterdir() if (path / "__init__.py").is_file()}

        assert set(self.LAYERS) == directories

    def test_every_layer_a_package_may_import_is_a_declared_package(self) -> None:
        assert all(allowed in self.LAYERS for layers in self.LAYERS.values() for allowed in layers)

    def test_the_package_graph_is_acyclic(self) -> None:
        assert all(package not in reaches(self.LAYERS, package, set()) for package in self.LAYERS)

    def test_the_reconstruction_engine_stays_clear_of_the_console_player(self) -> None:
        assert PLAYER not in reaches(self.LAYERS, "sampletones_core", set())

    def test_the_console_player_reads_the_reconstruction_engine(self) -> None:
        assert "sampletones_core" in self.LAYERS[PLAYER]


class TestPlayerGraph:
    """The player's own subpackages, and the order they may reach each other in."""

    LAYERS: Final[Dict[str, Tuple[str, ...]]] = check_import_boundary.PLAYER_LAYERS

    def test_every_layer_a_unit_may_import_is_a_declared_unit(self) -> None:
        assert all(allowed in self.LAYERS for layers in self.LAYERS.values() for allowed in layers)

    def test_the_player_graph_is_acyclic(self) -> None:
        assert all(unit not in reaches(self.LAYERS, unit, set()) for unit in self.LAYERS)

    def test_the_specification_is_the_layer_everything_stands_on(self) -> None:
        assert self.LAYERS["specification"] == ()

    def test_the_build_toolchain_is_reached_from_no_shipped_module(self) -> None:
        """`driver/assembler/` stays outside the wheel, so an import of it breaks an installed copy."""
        assert all("driver/assembler" not in layers for layers in self.LAYERS.values())

    def test_the_driver_is_reached_through_the_file_that_writes_the_nsf(self) -> None:
        assert "driver" in self.LAYERS["nsf"]

    def test_every_module_of_the_player_belongs_to_one_unit(self) -> None:
        rules = check_import_boundary.layer_rules(check_import_boundary.PLAYER_GRAPH)
        owners = Counter(path for rule in rules for path in reached_modules(rule))

        assert set(owners) == set(swept(SOURCE_ROOT / PLAYER))
        assert set(owners.values()) == {1}


class TestRuleModules:
    def test_a_module_directly_under_the_rule_directory_is_reached(self, tmp_path: Path) -> None:
        """`logic/**/*.py` names `logic/direct.py` as surely as `logic/inner/deep.py`."""
        direct = write_module(tmp_path / "logic", "direct.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(tmp_path, LOGIC_RULE, (), set(swept(tmp_path)), None)

        assert reached == [direct.resolve()]

    def test_a_module_nested_under_the_rule_directory_is_reached(self, tmp_path: Path) -> None:
        deep = write_module(tmp_path / "logic" / "inner", "deep.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(tmp_path, LOGIC_RULE, (), set(swept(tmp_path)), None)

        assert reached == [deep.resolve()]

    def test_a_module_outside_the_rule_directory_stays_aside(self, tmp_path: Path) -> None:
        write_module(tmp_path / "services", "conversion.py", PLAIN_IMPORT)

        assert check_import_boundary.rule_modules(tmp_path, LOGIC_RULE, (), set(swept(tmp_path)), None) == []

    def test_a_module_a_nested_rule_owns_is_left_to_it(self, tmp_path: Path) -> None:
        direct = write_module(tmp_path / "logic", "direct.py", PLAIN_IMPORT)
        write_module(tmp_path / "logic" / "inner", "deep.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(
            tmp_path,
            LOGIC_RULE,
            ("logic/inner/**/*.py",),
            set(swept(tmp_path)),
            None,
        )

        assert reached == [direct.resolve()]

    def test_a_selection_narrows_the_rule_to_the_files_it_names(self, tmp_path: Path) -> None:
        named = write_module(tmp_path / "logic", "named.py", PLAIN_IMPORT)
        write_module(tmp_path / "logic", "other.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(
            tmp_path,
            LOGIC_RULE,
            (),
            set(swept(tmp_path)),
            {named.resolve()},
        )

        assert reached == [named.resolve()]


class TestCheckBoundaries:
    def test_a_forbidden_import_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / APPLICATION / "logic", "direct.py", FORBIDDEN_IMPORT)

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert [violation.kind for violation in violations] == ["dearpygui"]

    def test_the_report_names_the_line_the_import_sits_on(self, tmp_path: Path) -> None:
        path = write_module(tmp_path / APPLICATION / "logic", "direct.py", f"{PLAIN_IMPORT}{FORBIDDEN_IMPORT}")

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert violations[0].location.startswith(f"{path}:2")

    def test_a_contract_module_stays_reachable(self, tmp_path: Path) -> None:
        """A layer reads another layer's data contract while its implementation stays out of reach."""
        write_module(tmp_path / APPLICATION / "logic", "direct.py", CONTRACT_IMPORT)

        assert check_import_boundary.check_boundaries(tmp_path, None) == []

    def test_an_allowed_import_reports_nothing(self, tmp_path: Path) -> None:
        write_module(tmp_path / APPLICATION / "logic", "direct.py", PLAIN_IMPORT)

        assert check_import_boundary.check_boundaries(tmp_path, None) == []

    def test_a_package_reaching_across_the_graph_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / "sampletones_core" / "formats", "player.py", PLAYER_IMPORT)

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert [violation.kind for violation in violations] == [PLAYER]

    def test_a_shipped_module_reaching_the_build_toolchain_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / PLAYER / "nsf", "file.py", ASSEMBLER_IMPORT)

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert [violation.kind for violation in violations] == ["sampletones_player.driver.assembler"]

    def test_the_build_toolchain_reads_the_driver_it_assembles(self, tmp_path: Path) -> None:
        body = "from sampletones_player.driver.image import DriverImage\n"
        write_module(tmp_path / PLAYER / "driver" / "assembler", "builder.py", body)

        assert check_import_boundary.check_boundaries(tmp_path, None) == []

    def test_a_forbidden_token_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / APPLICATION / "ui" / "panels", "left.py", PANEL_SUFFIX)

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert len(violations) == 1

    def test_a_selection_narrows_the_check(self, tmp_path: Path) -> None:
        checked = write_module(tmp_path / APPLICATION / "logic", "checked.py", FORBIDDEN_IMPORT)
        write_module(tmp_path / APPLICATION / "logic", "other.py", FORBIDDEN_IMPORT)

        violations = check_import_boundary.check_boundaries(tmp_path, {checked.resolve()})

        assert len(violations) == 1


class TestSweptRoots:
    """A root the sweep reads nothing under reports nothing, which reads as a clean tree."""

    def test_the_source_root_holds_modules(self) -> None:
        assert source_paths([SOURCE_ROOT])

    def test_every_boundary_rule_reaches_a_module(self) -> None:
        assert all(reached_modules(rule) for rule in check_import_boundary.RULES)

    def test_every_token_rule_reaches_a_module(self) -> None:
        rules = check_import_boundary.TOKEN_RULES
        assert all(list((SOURCE_ROOT / rule.root).glob(rule.pattern)) for rule in rules)

    def test_a_root_holding_no_module_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            check_import_boundary.check_boundaries(tmp_path, None)

    def test_an_absent_root_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(NotADirectoryError):
            check_import_boundary.check_boundaries(tmp_path / "absent", None)


class TestMain:
    def test_the_repository_holds_its_import_boundaries(self) -> None:
        assert check_import_boundary.main(["--all"]) == 0

    def test_a_forbidden_import_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = write_module(tmp_path / APPLICATION / "logic", "direct.py", FORBIDDEN_IMPORT)

        exit_code = check_import_boundary.main(["--all", "--source", str(tmp_path)])

        assert exit_code == 1
        error = capsys.readouterr().err
        assert f"{path}:1" in error
        assert "dearpygui" in error

    def test_named_files_narrow_the_run_to_themselves(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_module(tmp_path / APPLICATION / "logic", "reported.py", FORBIDDEN_IMPORT)
        clean = write_module(tmp_path / APPLICATION / "logic", "clean.py", PLAIN_IMPORT)

        assert check_import_boundary.main([str(clean), "--source", str(tmp_path)]) == 0
        assert capsys.readouterr().err == ""
