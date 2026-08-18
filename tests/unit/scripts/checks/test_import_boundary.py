from pathlib import Path
from typing import Final, List

import pytest

from sampletones_shared.meta.source.modules import source_paths
from tests.suite.scripts import load_script

check_import_boundary = load_script("checks/import_boundary.py")

LOGIC_RULE: Final[str] = "logic/**/*.py"

FORBIDDEN_IMPORT: Final[str] = "import dearpygui.dearpygui as dpg\n"
CONTRACT_IMPORT: Final[str] = "from sampletones_application.services.result import ServiceResult\n"
PLAIN_IMPORT: Final[str] = "from sampletones_core.project.project import Project\n"
PANEL_SUFFIX: Final[str] = "def build() -> None:\n    dpg.add_group(parent=SUF_PANEL_LEFT)\n"


def write_module(directory: Path, name: str, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def swept(package: Path) -> List[Path]:
    return [path.resolve() for path in source_paths([package])]


class TestRuleModules:
    def test_a_module_directly_under_the_rule_directory_is_reached(self, tmp_path: Path) -> None:
        """`logic/**/*.py` names `logic/direct.py` as surely as `logic/inner/deep.py`."""
        direct = write_module(tmp_path / "logic", "direct.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(tmp_path, LOGIC_RULE, set(swept(tmp_path)), None)

        assert reached == [direct.resolve()]

    def test_a_module_nested_under_the_rule_directory_is_reached(self, tmp_path: Path) -> None:
        deep = write_module(tmp_path / "logic" / "inner", "deep.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(tmp_path, LOGIC_RULE, set(swept(tmp_path)), None)

        assert reached == [deep.resolve()]

    def test_a_module_outside_the_rule_directory_stays_aside(self, tmp_path: Path) -> None:
        write_module(tmp_path / "services", "conversion.py", PLAIN_IMPORT)

        assert check_import_boundary.rule_modules(tmp_path, LOGIC_RULE, set(swept(tmp_path)), None) == []

    def test_a_selection_narrows_the_rule_to_the_files_it_names(self, tmp_path: Path) -> None:
        named = write_module(tmp_path / "logic", "named.py", PLAIN_IMPORT)
        write_module(tmp_path / "logic", "other.py", PLAIN_IMPORT)

        reached = check_import_boundary.rule_modules(
            tmp_path,
            LOGIC_RULE,
            set(swept(tmp_path)),
            {named.resolve()},
        )

        assert reached == [named.resolve()]


class TestCheckBoundaries:
    def test_a_forbidden_import_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / "logic", "direct.py", FORBIDDEN_IMPORT)

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert [violation.kind for violation in violations] == ["dearpygui"]

    def test_the_report_names_the_line_the_import_sits_on(self, tmp_path: Path) -> None:
        path = write_module(tmp_path / "logic", "direct.py", f"{PLAIN_IMPORT}{FORBIDDEN_IMPORT}")

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert violations[0].location.startswith(f"{path}:2")

    def test_a_contract_module_stays_reachable(self, tmp_path: Path) -> None:
        """A layer reads another layer's data contract while its implementation stays out of reach."""
        write_module(tmp_path / "logic", "direct.py", CONTRACT_IMPORT)

        assert check_import_boundary.check_boundaries(tmp_path, None) == []

    def test_an_allowed_import_reports_nothing(self, tmp_path: Path) -> None:
        write_module(tmp_path / "logic", "direct.py", PLAIN_IMPORT)

        assert check_import_boundary.check_boundaries(tmp_path, None) == []

    def test_a_forbidden_token_is_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path / "ui" / "panels", "left.py", PANEL_SUFFIX)

        violations = check_import_boundary.check_boundaries(tmp_path, None)

        assert len(violations) == 1

    def test_a_selection_narrows_the_check(self, tmp_path: Path) -> None:
        checked = write_module(tmp_path / "logic", "checked.py", FORBIDDEN_IMPORT)
        write_module(tmp_path / "logic", "other.py", FORBIDDEN_IMPORT)

        violations = check_import_boundary.check_boundaries(tmp_path, {checked.resolve()})

        assert len(violations) == 1


class TestSweptRoots:
    """A root the sweep reads nothing under reports nothing, which reads as a clean tree."""

    def test_the_application_package_holds_modules(self) -> None:
        assert source_paths([check_import_boundary.APP_ROOT])

    def test_every_boundary_rule_reaches_a_module(self) -> None:
        package = check_import_boundary.APP_ROOT
        assert all(list(package.glob(rule.pattern)) for rule in check_import_boundary.RULES)

    def test_every_token_rule_reaches_a_module(self) -> None:
        package = check_import_boundary.APP_ROOT
        assert all(list(package.glob(rule.pattern)) for rule in check_import_boundary.TOKEN_RULES)

    def test_a_package_holding_no_module_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            check_import_boundary.check_boundaries(tmp_path, None)

    def test_an_absent_package_stops_the_check(self, tmp_path: Path) -> None:
        with pytest.raises(NotADirectoryError):
            check_import_boundary.check_boundaries(tmp_path / "absent", None)


class TestMain:
    def test_the_repository_holds_its_layer_boundaries(self) -> None:
        assert check_import_boundary.main(["--all"]) == 0

    def test_a_forbidden_import_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = write_module(tmp_path / "logic", "direct.py", FORBIDDEN_IMPORT)

        exit_code = check_import_boundary.main(["--all", "--package", str(tmp_path)])

        assert exit_code == 1
        error = capsys.readouterr().err
        assert f"{path}:1" in error
        assert "dearpygui" in error

    def test_named_files_narrow_the_run_to_themselves(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_module(tmp_path / "logic", "reported.py", FORBIDDEN_IMPORT)
        clean = write_module(tmp_path / "logic", "clean.py", PLAIN_IMPORT)

        assert check_import_boundary.main([str(clean), "--package", str(tmp_path)]) == 0
        assert capsys.readouterr().err == ""
