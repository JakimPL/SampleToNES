from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones_tools.checks.boundary.packages import (
    NAMESPACE_PACKAGE,
    check_packages,
    enclosing_directories,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.source import write_module

INITIALIZER: Final[str] = "__init__.py"


def build_tree(root: Path, files: Tuple[str, ...]) -> None:
    """Writes each file a case names under ``root``, empty."""
    for file in files:
        relative = Path(file)
        write_module(root / relative.parent, relative.name, "")


def reported(root: Path) -> List[Path]:
    """The directories the check reports over a whole tree, relative to its root."""
    resolved = root.resolve()
    return [Path(violation.location).relative_to(resolved) for violation in check_packages(root, None)]


class TestEnclosingDirectories:
    def test_the_directories_run_from_the_innermost_and_leave_the_root_out(self, tmp_path: Path) -> None:
        module = tmp_path / "outer" / "inner" / "module.py"

        assert enclosing_directories(module, tmp_path) == (tmp_path / "outer" / "inner", tmp_path / "outer")

    def test_a_module_at_the_root_sits_in_no_directory(self, tmp_path: Path) -> None:
        assert enclosing_directories(tmp_path / "module.py", tmp_path) == ()


class TestCheckPackages(BaseTestSuite):
    """Every directory holding modules below the source root is a package of its own."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        files: Tuple[str, ...]
        expected: Tuple[str, ...]

    test_cases = (
        TestCase(
            label="a_directory_with_a_module",
            files=("package/module.py",),
            expected=("package",),
        ),
        TestCase(
            label="a_directory_holding_only_subpackages",
            files=(f"outer/inner/{INITIALIZER}", "outer/inner/module.py"),
            expected=("outer",),
        ),
        TestCase(
            label="every_directory_on_the_way_to_a_module",
            files=("outer/inner/module.py",),
            expected=("outer", "outer/inner"),
        ),
        TestCase(
            label="a_package_with_its_initializer",
            files=(f"package/{INITIALIZER}", "package/module.py"),
            expected=(),
        ),
        TestCase(
            label="a_data_only_directory",
            files=(f"package/{INITIALIZER}", "package/data/notes.txt", "package/data/table.yaml"),
            expected=(),
        ),
        TestCase(
            label="the_source_root_itself",
            files=("module.py",),
            expected=(),
        ),
        TestCase(
            label="a_hidden_directory",
            files=("module.py", ".cache/tool/module.py"),
            expected=(),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_check_packages(self, test_case: "TestCheckPackages.TestCase", tmp_path: Path) -> None:
        build_tree(tmp_path, test_case.files)

        assert reported(tmp_path) == [Path(directory) for directory in test_case.expected]


class TestCheckPackagesReport:
    def test_a_directory_is_reported_as_a_namespace_package(self, tmp_path: Path) -> None:
        build_tree(tmp_path, ("package/module.py",))

        violations = check_packages(tmp_path, None)

        assert [violation.kind for violation in violations] == [NAMESPACE_PACKAGE]
        assert Path(violations[0].location) == (tmp_path / "package").resolve()

    def test_a_selection_reports_the_directories_its_modules_sit_in(self, tmp_path: Path) -> None:
        build_tree(tmp_path, ("selected/module.py", "other/module.py"))
        selection = {(tmp_path / "selected" / "module.py").resolve()}

        violations = check_packages(tmp_path, selection)

        assert [Path(violation.location) for violation in violations] == [(tmp_path / "selected").resolve()]

    def test_a_tree_without_modules_stops_the_check(self, tmp_path: Path) -> None:
        build_tree(tmp_path, ("data/notes.txt",))

        with pytest.raises(FileNotFoundError):
            check_packages(tmp_path, None)
